#构件当前监测系统的增益系统
import pandas as pd
import numpy as np
import os
import itertools
import time
import gain_system_design

# 在 L_town_gain_fitness.py 顶部
_Q_H_dict_cache = {}

def get_cached_Q_H_table_dict(time_index):
    global _Q_H_dict_cache
    if time_index in _Q_H_dict_cache:
        return _Q_H_dict_cache[time_index] 
    if time_index == 0:
        fpath = r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_Q_H_pkl_1h.pkl"
    elif time_index == 1:
        fpath = r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_Q_H_pkl_4h.pkl"
    else:
        fpath = r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_Q_H_pkl_10h.pkl"
    #print(f"[子进程加载文件] 正在读取：{fpath}")
    with open(fpath, "rb") as f:
        _Q_H_dict_cache[time_index] = pd.read_pickle(f)
    return _Q_H_dict_cache[time_index]


def calculate_min_coverage_flow(current_Q_H_table,gain_system_combinations,gain_system_threshold):
    current_Q_H_table_values = (current_Q_H_table.iloc[:, 1:]).values
    smaller_H_decline= []
    larger_H_decline = []
    smaller_columns = []
    larger_columns = []
    corres_Q=[]
    for threshold_index in range(0,len(gain_system_threshold)):
        current_threshold=gain_system_threshold[threshold_index]
        current_combinations=gain_system_combinations[threshold_index]
        combination_rows=current_Q_H_table_values[list(current_combinations)]  # 提取行
        current_combination_sum_row=np.sum(combination_rows, axis=0)  # 按列求和
        reversed_current_combination_sum_row=current_combination_sum_row[::-1]
        insert_position=len(reversed_current_combination_sum_row)-np.searchsorted(reversed_current_combination_sum_row,current_threshold)
        if insert_position > 0:
            smaller = current_combination_sum_row[insert_position-1]
            smaller_column=current_Q_H_table.columns[insert_position]
        else:
            smaller = None  # 如果没有小于目标值的元素
            smaller_column = None
        if insert_position < len(reversed_current_combination_sum_row):
            larger =current_combination_sum_row[insert_position]
            larger_column = current_Q_H_table.columns[insert_position+1]
        else:
            larger = None  # 如果没有大于目标值的元素
            larger_column = None
        if smaller==None:#爆管响应压降很小，对应的爆管流量很小
            current_Q=0
        elif larger==None:#爆管响应压降很大，对应的爆管流量过大
            current_Q=np.inf
        else:
            current_Q=float(smaller_column)+(current_threshold-smaller)*(float(larger_column)-float(smaller_column))/(larger-smaller)
        smaller_H_decline.append(smaller)
        larger_H_decline.append(larger)
        smaller_columns.append(smaller_column)
        larger_columns.append(larger_column)
        corres_Q.append(current_Q)
    min_coverage_Q=min(corres_Q)
    return min_coverage_Q

def calculate_all_min_flow(Q_H_table_dict,gain_system_threshold,all_pipe_Qmax_list,gain_system_combinations):
    ##存放当前监测系统所有管道的最小可监测爆管流量
    all_pipe_min_coverage_Q=[]
    ##找选取节点阈值对应的各管段爆管流量
    for pipe_index in range(1,len(all_pipe_Qmax_list)+1):
        current_csv="p_"+str(pipe_index)+"_burst_Q_H.xlsx"
        current_Q_H_table=Q_H_table_dict[current_csv]
        min_coverage_Q=calculate_min_coverage_flow(current_Q_H_table,gain_system_combinations,gain_system_threshold)
        all_pipe_min_coverage_Q.append(min_coverage_Q)
    coverage_probability= [1 - (min_Q / b) for min_Q, b in zip(all_pipe_min_coverage_Q, all_pipe_Qmax_list)]
    # 示例数据
    coverage_probability_array= np.array(coverage_probability)
    coverage_probability_array= np.clip(coverage_probability_array, a_min=0, a_max=None)
    coverage_probability_list= coverage_probability_array.tolist()
    return coverage_probability_list



def get_gain_results(current_individual,all_pipe_Qmax_list,all_Q_H_path,covariance_matrix_dict,burst_H_decline_dict,sensitivity_threshold):
    current_individual_index= [x - 1 for x in current_individual]#当前个体物理传感器索引
    #设计增益系统
    population_size=100
    generations=50
    mutation_rate=0.2
    time_list=['1h','4h','10h']
    cover_ratio_list=[]
    coverage_probability_result_list=[]
    for time_index in range(0,3):
        current_time=time_list[time_index]
        covariance_matrix=covariance_matrix_dict[f"covariation_{current_time}.xlsx"]
        covariance_matrix_array=(covariance_matrix.iloc[:,-782:]).to_numpy()
        pipe_burst_matrix=burst_H_decline_dict[f"base_all_nodes_{current_time}_burst_data.xlsx"]
        pipe_burst_matrix_array=(pipe_burst_matrix.iloc[:,-905:]).to_numpy()
        pipe_burst_matrix_array=pipe_burst_matrix_array.T
        gain_system_combinations,gain_system_threshold,coverage_ratio,cover_list=gain_system_design.design_gain_system(current_individual_index,covariance_matrix_array,
                                                                                   pipe_burst_matrix_array, population_size, generations, 
                                                                                   mutation_rate,sensitivity_threshold)
        #计算最小覆盖流量
        current_Q_H_pkl_path=os.path.join(all_Q_H_path, f"all_Q_H_pkl_{current_time}.pkl")
        with open(current_Q_H_pkl_path, "rb") as f:
            current_Q_H_table_dict= pd.read_pickle(f)
        coverage_probability_list=calculate_all_min_flow(current_Q_H_table_dict,gain_system_threshold,all_pipe_Qmax_list,gain_system_combinations)
        coverage_probability_result=np.mean(coverage_probability_list)-0.01*np.std(coverage_probability_list)/np.mean(coverage_probability_list)
        cover_ratio_list.append(coverage_ratio)
        coverage_probability_result_list.append(coverage_probability_result)
    average_cover_ratio=sum(cover_ratio_list)/len(cover_ratio_list)
    average_coverage_probability_result=sum(coverage_probability_result_list)/len(coverage_probability_result_list)
    return average_cover_ratio,average_coverage_probability_result


#case
# current_individual=[1,5,3]
# with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_Q_H_pkl.pkl", "rb") as f:
#     Q_H_table_dict= pd.read_pickle(f)
# all_pipe_Qmax_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx", sheet_name='Sheet1'))['Qmax'].tolist()
# covariance_matrix_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\covariation_4h.xlsx"
# covariance_matrix=pd.read_excel(covariance_matrix_path, sheet_name='Sheet1')
# covariance_matrix_array=(covariance_matrix.iloc[:,-782:]).to_numpy()
# pipe_burst_matrix_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_nodes_4h_burst_data.xlsx"
# pipe_burst_matrix=pd.read_excel(pipe_burst_matrix_path, sheet_name='Sheet1')
# pipe_burst_matrix_array=(pipe_burst_matrix.iloc[:,-905:]).to_numpy()
# pipe_burst_matrix_array=pipe_burst_matrix_array.T
# population_size=50
# generations=50
# mutation_rate=0.2
# sensitivity_threshold=-4.22068293050037
# gain_system_combinations_original_index,gain_coverage_ratio,coverage_probability_result,all_pipe_best_sensitivity=get_gain_results(current_individual,Q_H_table_dict,all_pipe_Qmax_list,
#                                                                                     covariance_matrix_array,pipe_burst_matrix_array,population_size,
#                                                                                     generations,mutation_rate,sensitivity_threshold)
# print(gain_system_combinations_original_index)
# print(gain_coverage_ratio)
# print(coverage_probability_result)
# print(all_pipe_best_sensitivity)

# current_individual=[121,737,562,561,50,683,252,716]
# all_Q_H_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证"
# all_pipe_Qmax_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx", sheet_name='Sheet1'))['Qmax'].tolist()
# with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_covariation.pkl", "rb") as f:
#     covariance_matrix_dict= pd.read_pickle(f)
# with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl", "rb") as f:
#     burst_H_decline_dict= pd.read_pickle(f)
# sensitivity_threshold=-4.22068293050037
# average_cover_ratio,average_coverage_probability_result=get_gain_results(current_individual,all_Q_H_path,all_pipe_Qmax_list,covariance_matrix_dict,burst_H_decline_dict,sensitivity_threshold)


#case
# start_time = time.time()

# current_individual=[121,737,562,561]
# # all_Q_H_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证"
# # Q_H_pkl_path_1h=os.path.join(all_Q_H_path, "all_Q_H_pkl_1h.pkl")
# # with open(Q_H_pkl_path_1h, "rb") as f:
# #     Q_H_table_dict_1h= pd.read_pickle(f)
# # Q_H_pkl_path_4h=os.path.join(all_Q_H_path, "all_Q_H_pkl_4h.pkl")
# # with open(Q_H_pkl_path_4h, "rb") as f:
# #     Q_H_table_dict_4h= pd.read_pickle(f)
# # Q_H_pkl_path_10h=os.path.join(all_Q_H_path, "all_Q_H_pkl_10h.pkl")
# # with open(Q_H_pkl_path_10h, "rb") as f:
# #     Q_H_table_dict_10h= pd.read_pickle(f)
# all_pipe_Qmax_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx", sheet_name='Sheet1'))['Qmax'].tolist()
# with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_covariation.pkl", "rb") as f:
#     covariance_matrix_dict= pd.read_pickle(f)
# with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl", "rb") as f:
#     burst_H_decline_dict= pd.read_pickle(f)
# all_Q_H_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证"
# sensitivity_threshold=-4.22068293050037
# average_cover_ratio,average_coverage_probability_result=get_gain_results(current_individual,all_pipe_Qmax_list,all_Q_H_path,covariance_matrix_dict,burst_H_decline_dict,sensitivity_threshold)
# # 计算并输出运行时间
# end_time = time.time()
# all_execution_time = end_time - start_time
# print(f"代码执行时间: {all_execution_time}秒")

all_pipe_Qmax_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx", sheet_name='Sheet1'))['Qmax'].tolist()
all_Q_H_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证"
with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_covariation.pkl", "rb") as f:
    covariance_matrix_dict= pd.read_pickle(f)
with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl", "rb") as f:
    burst_H_decline_dict= pd.read_pickle(f)
sensitivity_threshold=-4.22068293050037
current_individual=np.array([352,193,726,516,82,397,347,50,719,594,646,268])#657,516,704,51,95,719,453,641,734,397,352,203
average_cover_ratio,average_coverage_probability_result=get_gain_results(current_individual,all_pipe_Qmax_list,all_Q_H_path,covariance_matrix_dict,burst_H_decline_dict,sensitivity_threshold)
print(average_cover_ratio)
print(average_coverage_probability_result)