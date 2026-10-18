import numpy as np
import time
import pandas as pd
import random
import math
import os
from multiprocessing import Pool
 

def initialize_population(clustered_node_list, pop_size, sensor_num):
    population = np.array([list(np.random.choice(clustered_node_list, sensor_num, replace=False)) for _ in range(pop_size)])
    return population


def calculate_threshold(burst_H_decline_table,current_individual_index):
    selected_rows=burst_H_decline_table.iloc[current_individual_index]
    selected_std=selected_rows['std']
    selected_threshold=[-x * 3 for x in selected_std]
    return selected_threshold

def calculate_DT(selected_Q_H_table,selected_threshold):
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
            current_Q=5000
        else:
            current_Q=float(smaller_column)+(current_threshold-smaller)*(float(larger_column)-float(smaller_column))/(larger-smaller)
        smaller_H_decline.append(smaller)
        larger_H_decline.append(larger)
        smaller_columns.append(smaller_column)
        larger_columns.append(larger_column)
        corres_Q.append(current_Q)
    min_DT=min(corres_Q)
    return min_DT

def calculate_current_ADT(Q_H_table_dict,selected_threshold, all_pipe_length, all_pipe_diam,current_individual_index):
    ##存放当前监测系统所有管道的最小可监测爆管流量
    all_pipe_min_DT=[]
    ##找选取节点阈值对应的各管段爆管流量
    for pipe_index in range(1,len(all_pipe_length)+1):
        current_csv="p_"+str(pipe_index)+"_burst_Q_H.xlsx"
        current_Q_H_table=Q_H_table_dict[current_csv]
        selected_Q_H_table=current_Q_H_table.iloc[current_individual_index]
        min_DT=calculate_DT(selected_Q_H_table,selected_threshold)
        all_pipe_min_DT.append(min_DT)
    all_pipe_DT= sum([min_Q*a*b for min_Q,a,b in zip(all_pipe_min_DT, all_pipe_length, all_pipe_diam)])
    len_dia_nominator=sum(x * y for x, y in zip(all_pipe_length,all_pipe_diam))
    # 示例数据
    current_ADT=all_pipe_DT/len_dia_nominator
    return current_ADT

def calculate_current_individual_ADT(burst_H_decline_dict, all_pipe_length, all_pipe_diam,all_Q_H_path,current_individual):
    current_individual_index= [x - 1 for x in current_individual]
    time_list=['1','4','10']
    all_ADT_list=[]
    for time_index in range(0,3):
        current_time=time_list[time_index]
        current_burst_H_decline_table=burst_H_decline_dict[f'base_all_nodes_{current_time}h_burst_data.xlsx'] #"base_all_nodes_{current_time}_burst_data.xlsx"
        selected_threshold=calculate_threshold(current_burst_H_decline_table,current_individual_index)
        current_Q_H_pkl_path=os.path.join(all_Q_H_path, f"all_Q_H_pkl_{current_time}h.pkl")
        with open(current_Q_H_pkl_path, "rb") as f:
            current_Q_H_table_dict= pd.read_pickle(f)
        current_ADT=calculate_current_ADT(current_Q_H_table_dict,selected_threshold,all_pipe_length,all_pipe_diam,current_individual_index)
        all_ADT_list.append(current_ADT)
    current_individual_ADT=sum(all_ADT_list)/len(all_ADT_list)
    return current_individual_ADT


def parallel_calculate_ADT_objectives(population,burst_H_decline_dict,all_pipe_length, all_pipe_diam,all_Q_H_path, num_workers=4):
    """并行计算目标函数值"""
    with Pool(processes=num_workers) as pool:
        # 为每个个体分配计算任务
        ADT_fitness_results= pool.starmap(calculate_current_individual_ADT, [(burst_H_decline_dict, all_pipe_length, all_pipe_diam,all_Q_H_path,individual) for individual in population])  
    ADT_fitness_array=np.array(ADT_fitness_results)
    return ADT_fitness_array


def select(population, ADT_fitness_array, tournament_size=3):
    #shared_fitness_array = compute_shared_fitness(sensitivity_fitness_array, population)
    population=np.array(population)
    sorted_ADT_fitness=np.argsort(ADT_fitness_array)
    better_index=sorted_ADT_fitness[:20]
    better_individual_array=population[better_index]
    selected_population = []
    for _ in range(len(population)-20):
        # 随机选择 tournament_size 个个体进行锦标赛
        tournament_indices = np.random.choice(population.shape[0], tournament_size, replace=False)
        tournament_fitness = ADT_fitness_array[tournament_indices]
        # 选择适应度最高的个体
        winner_index = tournament_indices[np.argmin(tournament_fitness)]
        selected_population.append(population[winner_index])
    selected_population_array=np.array(selected_population)
    selected_population=np.concatenate((better_individual_array,selected_population_array),axis=0)
    return selected_population


def ensure_bound(individual,clustered_node_list):
    seen = set()
    rep_idx = 0
    for i, val in enumerate(individual):
        if val in seen:
            while rep_idx < len(clustered_node_list) and (clustered_node_list[rep_idx] in seen):
                rep_idx += 1
            if rep_idx >= len(clustered_node_list):
                raise ValueError("replacement_list 中可用元素不足")
            individual[i] = clustered_node_list[rep_idx]
            seen.add(clustered_node_list[rep_idx])
            rep_idx += 1
        else:
            seen.add(val)
    return individual


# 交叉（单点交叉）
def crossover(parent1, parent2,clustered_node_list):
    child1=parent1.copy()
    child2=parent2.copy()
    if random.random() < 0.9:
        point = np.random.randint(1, len(parent1))
        child1 =np.concatenate((parent1[:point], parent2[point:]))
        child1=ensure_bound(child1,clustered_node_list)
        child2 =np.concatenate((parent2[:point], parent1[point:]))
        child2=ensure_bound(child2,clustered_node_list)
    return child1, child2
 
# 变异
def mutate(individual,mutation_rate,clustered_node_list):
    child = individual.copy()
    if random.random() < mutation_rate:
        remain_nodes=list(set(clustered_node_list)-set(individual.tolist()))
        replace_node = random.choice(remain_nodes)
        replace_index = np.random.randint(0, len(child))
        child[replace_index]=replace_node
    return child

 
# 遗传算法主函数
def genetic_algorithm(burst_H_decline_dict,clustered_node_list,sensor_num,generations_num,all_pipe_length, all_pipe_diam,all_Q_H_path):
    # 初始化种群
    population_size=200
    population = initialize_population(clustered_node_list, population_size, sensor_num)
    mutation_rate=0.3
    best_ADT_record=[]
    evolve_start_time = time.time()
    for generation in range(generations_num):
        print(generation)
        # 评估种群适应度
        ADT_fitness_array= parallel_calculate_ADT_objectives(population,burst_H_decline_dict,all_pipe_length, all_pipe_diam,all_Q_H_path, num_workers=4)
        best_ADT_record.append(np.min(ADT_fitness_array))
        # 选择
        selected_population = select(population, ADT_fitness_array, tournament_size=3)
        # 生成新种群
        new_population = []
        for i in range(0, len(selected_population), 2):
            parent1 = selected_population[i]
            parent2 = selected_population[i+1]
            child1, child2 = crossover(parent1,parent2,clustered_node_list)
            mutated_child1=mutate(child1,mutation_rate,clustered_node_list)
            mutated_child2=mutate(child2,mutation_rate,clustered_node_list)
            new_population.append(mutated_child1)
            new_population.append(mutated_child2)
        selected_new_population=select(new_population,ADT_fitness_array, tournament_size=3)
        indices= np.random.choice(np.arange(len(selected_new_population)), population_size-20, replace=False)
        population =np.concatenate((selected_population[:20],selected_new_population[indices]))
        #收敛判断
        unique_population=np.unique(population, axis=0)
        if len(best_ADT_record) >= 5:
            recent_diffs = np.abs(np.diff(best_ADT_record[-5:]))
            if np.max(recent_diffs) <0.01 and len(unique_population)<100:
                print(f"适应度收敛 & 种群相似度高，提前终止进化！")
                break
        current_gen_end_time = time.time()
        all_execution_time = current_gen_end_time - evolve_start_time
        print(all_execution_time)
    # 返回最佳个体
    unique_population=np.unique(population, axis=0)
    last_gen_ADT_fitness_array= parallel_calculate_ADT_objectives(unique_population,burst_H_decline_dict,all_pipe_length, all_pipe_diam,all_Q_H_path, num_workers=4)
    best_ADT_record.append(np.min(last_gen_ADT_fitness_array))
    last_gen_max_ADT_index= np.argsort(last_gen_ADT_fitness_array)[0]
    last_gen_best_sensors= unique_population[last_gen_max_ADT_index]
    current_gen_end_time = time.time()
    return last_gen_best_sensors,best_ADT_record[-1]



if __name__ == "__main__":
    for run in range(1,11):
        burst_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl"
        with open(burst_path,"rb") as f:#"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl"
            burst_H_decline_dict= pd.read_pickle(f)
        clustered_node_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_clustered_nodes.xlsx", sheet_name='Sheet1'))['index'].tolist()
        sensor_num=8
        generations_num=100
        all_pipe_length=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_infor.xlsx", sheet_name='Sheet1'))['length'].tolist()
        all_pipe_diam=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_infor.xlsx", sheet_name='Sheet1'))['diameter'].tolist()
        all_Q_H_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证"
        best_sensors,best_ADT=genetic_algorithm(burst_H_decline_dict,clustered_node_list,sensor_num,generations_num,all_pipe_length, all_pipe_diam,all_Q_H_path)
        optimization_results= np.hstack((best_sensors,best_ADT))
        df = pd.DataFrame([optimization_results])
        file_path = os.path.join(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\算法不确定性", f"Du_Kun_{run}.xlsx")
        df.to_excel(file_path, index=False, header=False)
        print(f"最优数据已成功写入 {file_path}")
    # current_individual=np.array([737,262,672,734,561,74,100,521])#616,443,641,683,516,336,422,352 #203,737,641,347,752,121,50,652 #391,463,50,52,432,635,443,397 #106,216,265,397,454,507,583,739
    # current_individual_ADT=calculate_current_individual_ADT(burst_H_decline_dict, all_pipe_length, all_pipe_diam,all_Q_H_path,current_individual)
    # print(current_individual_ADT)