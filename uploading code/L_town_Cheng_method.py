import numpy as np
import time
import pandas as pd
import random
import math
import os
from multiprocessing import Pool
from openpyxl import load_workbook
 

def initialize_population(clustered_node_list, pop_size, sensor_num, distance_matrix):
    population = []
    while len(population) < pop_size:
        individual = list(np.random.choice(clustered_node_list, sensor_num, replace=False))
        if is_valid_by_distance(individual, distance_matrix):
            population.append(individual)
    return np.array(population)


def calculate_current_individual_LQG(all_LQG_dict,current_individual):
    current_individual_index= [x - 1 for x in current_individual]
    time_list=['1h','4h','10h']
    all_LQG_list=[]
    for time_index in range(0,3):
        current_time=time_list[time_index]
        current_time_LQG_table=all_LQG_dict[f"cheng_LQG_{current_time}.xlsx"]
        selected_rows=current_time_LQG_table.iloc[current_individual_index]
        selected_rows_matrix=current_time_LQG_table.iloc[current_individual_index, -905:]
        current_LQG=selected_rows_matrix.to_numpy().sum()
        all_LQG_list.append(current_LQG)
    current_individual_LQG=sum(all_LQG_list)/len(all_LQG_list)
    return current_individual_LQG


def parallel_calculate_LQG_objectives(population,all_LQG_dict, num_workers=4):
    """并行计算目标函数值"""
    with Pool(processes=num_workers) as pool:
        # 为每个个体分配计算任务
        LQG_fitness_results= pool.starmap(calculate_current_individual_LQG, [(all_LQG_dict,individual) for individual in population])  
    LQG_fitness_array=np.array(LQG_fitness_results)
    return LQG_fitness_array


def select(population,LQG_fitness_array, tournament_size=3):
    #shared_fitness_array = compute_shared_fitness(sensitivity_fitness_array, population)
    population=np.array(population)
    sorted_LQG_fitness=np.argsort(-LQG_fitness_array)
    better_index=sorted_LQG_fitness[:20]
    better_individual_array=population[better_index]
    selected_population = []
    for _ in range(len(population)-20):
        # 随机选择 tournament_size 个个体进行锦标赛
        tournament_indices = np.random.choice(population.shape[0], tournament_size, replace=False)
        tournament_fitness = LQG_fitness_array[tournament_indices]
        # 选择适应度最高的个体
        winner_index = tournament_indices[np.argmax(tournament_fitness)]
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
def crossover(parent1, parent2,clustered_node_list, distance_matrix):
    child1=parent1.copy()
    child2=parent2.copy()
    if random.random() < 0.9:
        point = np.random.randint(1, len(parent1))
        child1 =np.concatenate((parent1[:point], parent2[point:]))
        child1=ensure_bound(child1,clustered_node_list)
        child2 =np.concatenate((parent2[:point], parent1[point:]))
        child2=ensure_bound(child2,clustered_node_list)
        # 添加约束判断
        if not is_valid_by_distance(child1, distance_matrix):
            child1 = parent1.copy()
        if not is_valid_by_distance(child2, distance_matrix):
            child2 = parent2.copy()
    return child1, child2
 
# 变异
def mutate(individual,mutation_rate,clustered_node_list, distance_matrix):
    child = individual.copy()
    if random.random() < mutation_rate:
        remain_nodes=list(set(clustered_node_list)-set(individual.tolist()))
        replace_node = random.choice(remain_nodes)
        replace_index = np.random.randint(0, len(child))
        original_node = child[replace_index]
        child[replace_index]=replace_node
        if not is_valid_by_distance(child, distance_matrix):
            child[replace_index] = original_node  # 恢复原值
    return child

def is_valid_by_distance(individual, distance_matrix, min_distance=140):
    sub_matrix = distance_matrix[np.ix_([i - 1 for i in individual], [i - 1 for i in individual])]
    # 取上三角（不含对角线）的所有距离
    triu_indices = np.triu_indices(len(individual), k=1)
    pairwise_distances = sub_matrix[triu_indices]
    return np.all(pairwise_distances >= min_distance)
 
# 遗传算法主函数
def genetic_algorithm(all_LQG_dict,clustered_node_list,sensor_num,generations_num, distance_matrix):
    # 初始化种群
    population_size=100
    population = initialize_population(clustered_node_list, population_size, sensor_num, distance_matrix)
    mutation_rate=0.3
    best_LQG_record=[]
    evolve_start_time = time.time()
    for generation in range(generations_num):
        # 评估种群适应度
        LQG_fitness_array= parallel_calculate_LQG_objectives(population,all_LQG_dict, num_workers=4)
        best_LQG_record.append(np.max(LQG_fitness_array))
        # 选择
        selected_population = select(population, LQG_fitness_array, tournament_size=3)
        # 生成新种群
        new_population = []
        for i in range(0, len(selected_population), 2):
            parent1 = selected_population[i]
            parent2 = selected_population[i+1]
            child1, child2 = crossover(parent1,parent2,clustered_node_list, distance_matrix)
            mutated_child1=mutate(child1,mutation_rate,clustered_node_list, distance_matrix)
            mutated_child2=mutate(child2,mutation_rate,clustered_node_list, distance_matrix)
            new_population.append(mutated_child1)
            new_population.append(mutated_child2)
        selected_new_population=select(new_population,LQG_fitness_array, tournament_size=3)
        indices= np.random.choice(np.arange(len(selected_new_population)), population_size-20, replace=False)
        population =np.concatenate((selected_population[:20],selected_new_population[indices]))
        #收敛判断
        unique_population=np.unique(population, axis=0)
        if len(best_LQG_record) >= 5:
            recent_diffs = np.abs(np.diff(best_LQG_record[-5:]))
            if np.max(recent_diffs) <0.01 and len(unique_population)<100:
                print(f"适应度收敛 & 种群相似度高，提前终止进化！")
                break
        current_gen_end_time = time.time()
        all_execution_time = current_gen_end_time - evolve_start_time
        print(all_execution_time)
    # 返回最佳个体
    unique_population=np.unique(population, axis=0)
    last_gen_LQG_fitness_array= parallel_calculate_LQG_objectives(unique_population,all_LQG_dict, num_workers=4)
    best_LQG_record.append(np.max(last_gen_LQG_fitness_array))
    last_gen_max_LQG_index= np.argsort(-last_gen_LQG_fitness_array)[0]
    last_gen_best_sensors= unique_population[last_gen_max_LQG_index]
    current_gen_end_time = time.time()
    return last_gen_best_sensors,best_LQG_record[-1]

if __name__ == "__main__":
    distance_workbook= load_workbook(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\Cheng_nodes_distance_matrix.xlsx", data_only=True)
    distance_worksheet=distance_workbook["Sheet1"]
    distance_range =distance_worksheet["B2:ADC783"]
    distance_matrix= np.array([[cell.value for cell in row] for row in distance_range])
    with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_cheng_LQG.pkl","rb") as f:
        all_LQG_dict= pd.read_pickle(f)
    clustered_node_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_clustered_nodes.xlsx", sheet_name='Sheet1'))['index'].tolist()
    sensor_num=8
    generations_num=50
    for run in range(1,11):
        best_sensors,best_LQG=genetic_algorithm(all_LQG_dict,clustered_node_list,sensor_num,generations_num, distance_matrix)
        optimization_results= np.hstack((best_sensors,best_LQG))
        df = pd.DataFrame([optimization_results])
        file_path = os.path.join(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\算法不确定性", f"Cheng_{run}.xlsx")
        df.to_excel(file_path, index=False, header=False)
        print(f"最优数据已成功写入 {file_path}")
    