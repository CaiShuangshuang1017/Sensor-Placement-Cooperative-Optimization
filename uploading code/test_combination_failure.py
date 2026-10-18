import os
import numpy as np
import pandas as pd
import random

_Q_H_dict_cache={}

def preload_Q_H_table_dict():
    global _Q_H_dict_cache
    file_dict={
        0:r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_Q_H_pkl_1h.pkl",
        1:r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_Q_H_pkl_4h.pkl",
        2:r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_Q_H_pkl_10h.pkl"
    }
    for time_index,fpath in file_dict.items():
        with open(fpath,"rb") as f:
            _Q_H_dict_cache[time_index]=pd.read_pickle(f)
    print("Q-H数据已全部加载到内存")

def evaluate_fixed_gain_system(gain_system_combinations_index,covariance_matrix_array,pipe_burst_matrix_array,sensitivity_threshold):
    gain_system_threshold=[]
    for combination in gain_system_combinations_index:
        idx=np.array(combination,dtype=int)
        sub_covariance=covariance_matrix_array[np.ix_(idx,idx)]
        weight=np.ones(len(idx))
        variance=weight@sub_covariance@weight
        std=np.sqrt(max(variance,0))
        gain_system_threshold.append(std*sensitivity_threshold)
    gain_system_threshold=np.array(gain_system_threshold)

    cover_list=[]
    for pipe_index in range(pipe_burst_matrix_array.shape[0]):
        covered=0
        for combination,threshold in zip(gain_system_combinations_index,gain_system_threshold):
            H_decline=np.sum(pipe_burst_matrix_array[pipe_index,combination])
            if H_decline<threshold:
                covered=1
                break
        cover_list.append(covered)

    coverage_ratio=np.mean(cover_list)
    return gain_system_threshold,coverage_ratio,cover_list


def calculate_min_coverage_flow(current_Q_H_table,gain_system_combinations_index,gain_system_threshold):
    current_Q_H_table_values=current_Q_H_table.iloc[:,1:].values
    corres_Q=[]

    for threshold_index in range(len(gain_system_threshold)):
        current_threshold=gain_system_threshold[threshold_index]
        current_combination=gain_system_combinations_index[threshold_index]

        combination_rows=current_Q_H_table_values[current_combination]
        current_combination_sum_row=np.sum(combination_rows,axis=0)
        reversed_row=current_combination_sum_row[::-1]

        insert_position=len(reversed_row)-np.searchsorted(reversed_row,current_threshold)

        if insert_position>0:
            smaller=current_combination_sum_row[insert_position-1]
            smaller_column=current_Q_H_table.columns[insert_position]
        else:
            smaller=None
            smaller_column=None

        if insert_position<len(reversed_row):
            larger=current_combination_sum_row[insert_position]
            larger_column=current_Q_H_table.columns[insert_position+1]
        else:
            larger=None
            larger_column=None

        if smaller is None:
            current_Q=0
        elif larger is None:
            current_Q=np.inf
        elif larger==smaller:
            current_Q=float(smaller_column)
        else:
            current_Q=float(smaller_column)+(current_threshold-smaller)*(float(larger_column)-float(smaller_column))/(larger-smaller)

        corres_Q.append(current_Q)

    return min(corres_Q)


def calculate_all_min_flow(Q_H_table_dict,gain_system_threshold,all_pipe_Qmax_list,gain_system_combinations_index):
    all_pipe_min_coverage_Q=[]

    for pipe_index in range(1,len(all_pipe_Qmax_list)+1):
        current_csv=f"p_{pipe_index}_burst_Q_H.xlsx"
        current_Q_H_table=Q_H_table_dict[current_csv]

        min_coverage_Q=calculate_min_coverage_flow(
            current_Q_H_table,
            gain_system_combinations_index,
            gain_system_threshold
        )
        all_pipe_min_coverage_Q.append(min_coverage_Q)

    coverage_probability=[
        1-(min_Q/Qmax)
        for min_Q,Qmax in zip(all_pipe_min_coverage_Q,all_pipe_Qmax_list)
    ]

    coverage_probability=np.array(coverage_probability,dtype=float)
    coverage_probability=np.clip(coverage_probability,a_min=0,a_max=None)

    return coverage_probability.tolist()


def get_gain_results(gain_system_combinations,all_pipe_Qmax_list,
                     covariance_matrix_dict,burst_H_decline_dict,sensitivity_threshold):

    if len(gain_system_combinations)==0:
        return 0.0,0.0

    # 节点编号统一转换为0-based index
    gain_system_combinations_index=[
        [int(x)-1 for x in combination]
        for combination in gain_system_combinations
    ]

    time_list=['1h','4h','10h']
    cover_ratio_list=[]
    coverage_probability_result_list=[]

    for time_index in range(3):
        current_time=time_list[time_index]

        covariance_matrix=covariance_matrix_dict[f"covariation_{current_time}.xlsx"]
        covariance_matrix_array=covariance_matrix.iloc[:,-782:].to_numpy()

        pipe_burst_matrix=burst_H_decline_dict[f"base_all_nodes_{current_time}_burst_data.xlsx"]
        pipe_burst_matrix_array=pipe_burst_matrix.iloc[:,-905:].to_numpy().T

        gain_system_threshold,coverage_ratio,cover_list=evaluate_fixed_gain_system(
            gain_system_combinations_index,
            covariance_matrix_array,
            pipe_burst_matrix_array,
            sensitivity_threshold
        )

        # 直接从内存读取Q-H数据
        current_Q_H_table_dict=_Q_H_dict_cache[time_index]

        coverage_probability_list=calculate_all_min_flow(
            current_Q_H_table_dict,
            gain_system_threshold,
            all_pipe_Qmax_list,
            gain_system_combinations_index
        )

        # 当前时刻BCP指标
        mean_probability=np.mean(coverage_probability_list)
        if mean_probability>0:
            coverage_probability_result=mean_probability-0.01*np.std(coverage_probability_list)/mean_probability
        else:
            coverage_probability_result=0.0

        # 保存当前时刻结果
        cover_ratio_list.append(coverage_ratio)
        coverage_probability_result_list.append(coverage_probability_result)

    # 1h、4h、10h取平均
    average_cover_ratio=np.mean(cover_ratio_list)
    average_coverage_probability_result=np.mean(coverage_probability_result_list)

    return average_cover_ratio,average_coverage_probability_result



import itertools

def exhaustive_failure_analysis(gain_system_combinations,all_pipe_Qmax_list,
                                covariance_matrix_dict,burst_H_decline_dict,
                                sensitivity_threshold):

    all_sensors=sorted(set(
        sensor for combination in gain_system_combinations
        for sensor in combination
    ))

    print("物理传感器总数:",len(all_sensors))
    print("物理传感器:",all_sensors)
    print("原始合作组合数量:",len(gain_system_combinations))

    detailed_results=[]

    # 0个失效：基准情况
    base_cover,base_probability=get_gain_results(
        gain_system_combinations,
        all_pipe_Qmax_list,
        covariance_matrix_dict,
        burst_H_decline_dict,
        sensitivity_threshold
    )

    detailed_results.append({
        "failed_num":0,
        "scenario":0,
        "failed_sensors":"",
        "remaining_combination_num":len(gain_system_combinations),
        "average_cover_ratio":base_cover,
        "average_coverage_probability_result":base_probability
    })

    print(f"\n失效数量=0, coverage={base_cover:.6f}, probability={base_probability:.6f}")

    # 从失效1个一直遍历到全部传感器失效
    for failed_num in range(1,len(all_sensors)+1):

        failure_scenarios=list(itertools.combinations(all_sensors,failed_num))
        scenario_num=len(failure_scenarios)

        print(f"\n========== 失效 {failed_num} 个传感器 ==========")
        print("失效场景总数:",scenario_num)

        for scenario_index,failed_sensors in enumerate(failure_scenarios,1):
            failed_set=set(failed_sensors)

            # 只要组合中包含任意失效传感器，该组合整体删除
            available_combinations=[
                combination for combination in gain_system_combinations
                if failed_set.isdisjoint(combination)
            ]

            if len(available_combinations)==0:
                average_cover_ratio=0.0
                average_probability=0.0
            else:
                average_cover_ratio,average_probability=get_gain_results(
                    available_combinations,
                    all_pipe_Qmax_list,
                    covariance_matrix_dict,
                    burst_H_decline_dict,
                    sensitivity_threshold
                )

            detailed_results.append({
                "failed_num":failed_num,
                "scenario":scenario_index,
                "failed_sensors":",".join(map(str,failed_sensors)),
                "remaining_combination_num":len(available_combinations),
                "average_cover_ratio":average_cover_ratio,
                "average_coverage_probability_result":average_probability
            })

            print(
                f"{scenario_index}/{scenario_num}, "
                f"failed={failed_sensors}, "
                f"remaining={len(available_combinations)}, "
                f"coverage={average_cover_ratio:.6f}, "
                f"probability={average_probability:.6f}"
            )

    detailed_df=pd.DataFrame(detailed_results)

    summary_df=detailed_df.groupby("failed_num").agg(
        scenario_num=("scenario","count"),
        mean_cover_ratio=("average_cover_ratio","mean"),
        std_cover_ratio=("average_cover_ratio","std"),
        min_cover_ratio=("average_cover_ratio","min"),
        max_cover_ratio=("average_cover_ratio","max"),
        mean_coverage_probability=("average_coverage_probability_result","mean"),
        std_coverage_probability=("average_coverage_probability_result","std"),
        min_coverage_probability=("average_coverage_probability_result","min"),
        max_coverage_probability=("average_coverage_probability_result","max"),
        mean_remaining_combination_num=("remaining_combination_num","mean")
    ).reset_index()

    summary_df=summary_df.fillna(0)

    return detailed_df,summary_df


# ============================================================
# 主程序
# ============================================================

# 固定合作组合Excel
population_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\gain_12_combinations.xlsx"
population_df=pd.read_excel(population_path)

gain_system_combinations=[]
for _,row in population_df.iterrows():
    combination=[int(x) for x in row.dropna()]
    if combination:
        gain_system_combinations.append(combination)

# Qmax
all_pipe_Qmax_list=pd.read_excel(
    r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx",
    sheet_name="Sheet1"
)["Qmax"].tolist()



with open(
    r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_covariation.pkl",
    "rb"
) as f:
    covariance_matrix_dict=pd.read_pickle(f)

with open(
    r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl",
    "rb"
) as f:
    burst_H_decline_dict=pd.read_pickle(f)

sensitivity_threshold=-4.22068293050037

# 一次性加载1h、4h、10h的Q-H数据库
preload_Q_H_table_dict()


detailed_df,summary_df=exhaustive_failure_analysis(
    gain_system_combinations,
    all_pipe_Qmax_list,
    covariance_matrix_dict,
    burst_H_decline_dict,
    sensitivity_threshold
)

output_path=r"D:\xxx\gain_system_failure_results.xlsx"

with pd.ExcelWriter(output_path,engine="openpyxl") as writer:
    detailed_df.to_excel(writer,sheet_name="Detailed",index=False)
    summary_df.to_excel(writer,sheet_name="Summary",index=False)

print("\n===== Summary =====")
print(summary_df.to_string(index=False))
print("\n保存至:",output_path)