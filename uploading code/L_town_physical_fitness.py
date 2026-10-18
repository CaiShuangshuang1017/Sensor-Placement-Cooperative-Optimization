import numpy as np
import time
import pandas as pd
import os

#覆盖率计算
def calculate_coverage_ratio(burst_H_decline_table,pipe_num,sensitivity_threshold,current_individual_index):
    selected_rows=burst_H_decline_table.iloc[current_individual_index]
    selected_std=selected_rows['std']
    selected_burst_decline=selected_rows.iloc[:,-pipe_num:]
    selected_sensitivity=selected_burst_decline.div(selected_std, axis=0)
    selected_max_sensitivity=selected_sensitivity.min()
    cover_ratio=((selected_max_sensitivity<sensitivity_threshold).sum())/pipe_num
    ##获取选取节点的覆盖阈值
    selected_threshold=selected_rows['threshold_5%_0.5%']
    selected_threshold=selected_threshold.tolist()
    return cover_ratio,selected_threshold

def calculate_min_coverage_flow(selected_Q_H_table,selected_threshold):
    selected_Q_H_table_values = (selected_Q_H_table.iloc[:, 1:]).values
    smaller_H_decline= []
    larger_H_decline = []
    smaller_columns = []
    larger_columns = []
    corres_Q=[]
    for i in range(selected_Q_H_table_values.shape[0]):
        current_threshold=selected_threshold[i]
        current_Q_H_row= selected_Q_H_table_values[i]
        reversed_current_Q_H_row =current_Q_H_row[::-1]
        insert_position=len(reversed_current_Q_H_row)-np.searchsorted(reversed_current_Q_H_row,current_threshold)
        if insert_position > 0:
            smaller = current_Q_H_row[insert_position-1]
            smaller_column=selected_Q_H_table.columns[insert_position]
        else:
            smaller = None  # 如果没有小于目标值的元素
            smaller_column = None
        if insert_position < len(reversed_current_Q_H_row):
            larger =current_Q_H_row[insert_position]
            larger_column = selected_Q_H_table.columns[insert_position+1]
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
    # # 输出结果
    # print("Smaller values and corresponding columns:")
    # for i, value in enumerate(selected_threshold):
    #     print(f"对于值 {value}:")
    #     print(f"正好小于其的数及表头: {smaller_H_decline[i]} ({smaller_columns[i]})")
    #     print(f"正好大于其的数及表头: {larger_H_decline[i]} ({larger_columns[i]})")
    #     print(f"该值对应的流量 {corres_Q[i]}:")
    min_coverage_Q=min(corres_Q)
    return min_coverage_Q

def calculate_all_min_flow(Q_H_table_dict,selected_threshold,all_pipe_Qmax_list,current_individual_index):
    
    ##存放当前监测系统所有管道的最小可监测爆管流量
    all_pipe_min_coverage_Q=[]
    ##找选取节点阈值对应的各管段爆管流量
    for pipe_index in range(1,len(all_pipe_Qmax_list)+1):
        current_csv="p_"+str(pipe_index)+"_burst_Q_H.xlsx"
        current_Q_H_table=Q_H_table_dict[current_csv]
        selected_Q_H_table=current_Q_H_table.iloc[current_individual_index]
        min_coverage_Q=calculate_min_coverage_flow(selected_Q_H_table,selected_threshold)
        all_pipe_min_coverage_Q.append(min_coverage_Q)
    coverage_probability= [1 - (min_Q / b) for min_Q, b in zip(all_pipe_min_coverage_Q, all_pipe_Qmax_list)]
    # 示例数据
    coverage_probability_array= np.array(coverage_probability)
    coverage_probability_array= np.clip(coverage_probability_array, a_min=0, a_max=None)
    coverage_probability_list= coverage_probability_array.tolist()
    return coverage_probability_list


def calculate_coverage_ratio_probability(burst_H_decline_dict,all_pipe_Qmax_list,all_Q_H_path,sensitivity_threshold,current_individual,vari_coef):
    current_individual_index= [x - 1 for x in current_individual]
    pipe_num=len(all_pipe_Qmax_list)
    time_list=['1h','4h','10h']
    cover_ratio_list=[]
    coverage_probability_result_list=[]
    for time_index in range(0,3):
        current_time=time_list[time_index]
        current_burst_H_decline_table=burst_H_decline_dict[f"base_all_nodes_{current_time}_burst_data.xlsx"]
        current_Q_H_pkl_path=os.path.join(all_Q_H_path, f"all_Q_H_pkl_{current_time}.pkl")
        with open(current_Q_H_pkl_path, "rb") as f:
            current_Q_H_table_dict= pd.read_pickle(f)
        cover_ratio,selected_threshold=calculate_coverage_ratio(current_burst_H_decline_table,pipe_num,sensitivity_threshold,current_individual_index)
        coverage_probability_list=calculate_all_min_flow(current_Q_H_table_dict,selected_threshold,all_pipe_Qmax_list,current_individual_index)
        coverage_probability_result=np.mean(coverage_probability_list)-vari_coef*np.std(coverage_probability_list)/np.mean(coverage_probability_list)
        cover_ratio_list.append(cover_ratio)
        coverage_probability_result_list.append(coverage_probability_result)
    average_cover_ratio=sum(cover_ratio_list)/len(cover_ratio_list)
    average_coverage_probability_result=sum(coverage_probability_result_list)/len(coverage_probability_result_list)
    return average_cover_ratio,average_coverage_probability_result


###case
# start_time = time.time()
# burst_H_decline_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_nodes_4h_burst_data.xlsx"
# burst_H_decline_table= pd.read_excel(burst_H_decline_path, sheet_name='Sheet1')
# Q_H_table_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\L_town_burst_Q_H"
# all_pipe_Qmax_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx"
# all_pipe_Qmax_list=(pd.read_excel(all_pipe_Qmax_path, sheet_name='Sheet1'))['Qmax'].tolist()
# sensitivity_threshold=-4.22068293050037
# vari_coef=0.01

# #case individual
# clustered_node_list_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_4h_clustered_nodes.xlsx"
# population_size=1
# sensor_num=8
# clustered_node_list=(pd.read_excel(clustered_node_list_path, sheet_name='Sheet1'))['index'].tolist()
# population = [list(np.random.choice(clustered_node_list, sensor_num, replace=False)) for _ in range(population_size)]

# ##
# cover_ratio,coverage_probability_result=calculate_coverage_ratio_probability(burst_H_decline_table,all_pipe_Qmax_list,Q_H_table_path,sensitivity_threshold,population[0],vari_coef)
# print(cover_ratio)
# print(coverage_probability_result)
# end_time = time.time()
# # 计算并输出运行时间
# execution_time = end_time - start_time
# print(f"代码执行时间: {execution_time}秒")

# with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl", "rb") as f:
#     burst_H_decline_dict= pd.read_pickle(f)
# all_pipe_Qmax_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx", sheet_name='Sheet1'))['Qmax'].tolist()
# all_Q_H_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证"
# sensitivity_threshold=-4.22068293050037
# current_individual=np.array([352,193,726,516,82,397,347,50,719,594,646,268])#616,443,641,683,516,336,422,352 #203,737,641,347,752,121,50,652 #391,463,50,52,432,635,443,397 #106,216,265,397,454,507,583,739#737,262,672,734,561,74,100,521 #347,203,268,516,252,74,397,50
# #657,516,704,51,95,719,453,641,734,397,352,203
# vari_coef=0.01
# average_cover_ratio,average_coverage_probability_result=calculate_coverage_ratio_probability(burst_H_decline_dict,all_pipe_Qmax_list,all_Q_H_path,sensitivity_threshold,current_individual,vari_coef)
# print(average_cover_ratio)
# print(average_coverage_probability_result)