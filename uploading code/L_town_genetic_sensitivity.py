import numpy as np
import time
import pandas as pd
import random
import math
from multiprocessing import Pool
 

def initialize_population(clustered_node_list_1, clustered_node_list_2, pop_size, sensor_num):
    select_ratio=len(clustered_node_list_1)/(len(clustered_node_list_1)+len(clustered_node_list_2))
    population = np.array([(lambda num_1: list(np.random.choice(clustered_node_list_1, num_1, replace=False))
                            +list(np.random.choice(clustered_node_list_2, sensor_num - num_1, replace=False)))
                            (np.random.randint(1, math.ceil(sensor_num*select_ratio) + 1)) for _ in range(pop_size)])
    return population
 


def calculate_fitness(current_individual,covariance_matrix_dict,burst_H_decline_dict):
    current_individual_index= [x - 1 for x in current_individual]#当前个体物理传感器索引
    time_list=['1h','4h','10h']
    std_list=[]
    H_decline_list=[]
    for time_index in range(0,3):
        current_time=time_list[time_index]
        covariance_matrix=covariance_matrix_dict[f"covariation_{current_time}.xlsx"]
        covariance_matrix_array=(covariance_matrix.iloc[:,-782:]).to_numpy()
        current_sub_covariance_array=covariance_matrix_array[np.ix_(current_individual_index,current_individual_index)]
        current_sum_covariance=np.sum(current_sub_covariance_array)
        std_list.append(current_sum_covariance)
        pipe_burst_matrix=burst_H_decline_dict[f"base_all_nodes_{current_time}_burst_data.xlsx"]
        pipe_burst_matrix_array=(pipe_burst_matrix.iloc[:,-905:]).to_numpy()
        current_sub_burst_array=pipe_burst_matrix_array[current_individual_index,:]
        current_burst_array_sums = np.sum(current_sub_burst_array, axis=0)
        current_sum_decline=np.mean(current_burst_array_sums)-0.01*np.std(current_burst_array_sums)/np.mean(current_burst_array_sums)
        H_decline_list.append(current_sum_decline)
    average_std=sum(std_list)/len(std_list)
    average_H_decline=sum(H_decline_list)/len(H_decline_list)
    current_sensitivity_fitness=average_H_decline/average_std
    return current_sensitivity_fitness

def parallel_calculate_low_objectives(population,burst_H_decline_dict,covariance_matrix_dict, num_workers=4):
    """并行计算目标函数值"""
    with Pool(processes=num_workers) as pool:
        # 为每个个体分配计算任务
        sensitivity_fitness_results= pool.starmap(calculate_fitness, [(individual,covariance_matrix_dict,burst_H_decline_dict) for individual in population])  
    sensitivity_fitness_array=np.array(sensitivity_fitness_results)
    return sensitivity_fitness_array

# def compute_shared_fitness(sensitivity_fitness_array, population):
#     population = np.array(population)  # 确保为 NumPy 数组
#     population_size, gene_count = population.shape
#     shared_fitness = np.zeros(population_size)
#     # 计算交集矩阵 & 并集矩阵
#     intersection_matrix = np.zeros((population_size, population_size), dtype=int)
#     for i in range(population_size):
#         for j in range(i + 1, population_size):  # 只计算上三角部分，减少重复
#             intersection_matrix[i, j] = np.intersect1d(population[i], population[j]).size
#             intersection_matrix[j, i] = intersection_matrix[i, j]  # 对称填充
#     union_size = 2 * gene_count - intersection_matrix  # 并集大小
#     jaccard_distance = 1 - (intersection_matrix / union_size)  # 计算 Jaccard 距离
#     # 计算共享因子
#     sigma_share=0.5
#     alpha=1
#     sharing_function = np.where(jaccard_distance < sigma_share, (1 - (jaccard_distance / sigma_share) ** alpha), 0)
#     sharing_sums = np.sum(sharing_function, axis=1)
#     # 计算共享适应度
#     coef=0.01/max(0.0000001,np.max(sharing_sums))
#     shared_fitness = sensitivity_fitness_array/(1 +coef*sharing_sums)
#     return shared_fitness


def select(population, sensitivity_fitness_array, tournament_size=3):
    #shared_fitness_array = compute_shared_fitness(sensitivity_fitness_array, population)
    population=np.array(population)
    sorted_sensitivity_fitness=np.argsort(sensitivity_fitness_array)
    better_index=sorted_sensitivity_fitness[:20]
    better_individual_array=population[better_index]
    selected_population = []
    for _ in range(len(population)-20):
        # 随机选择 tournament_size 个个体进行锦标赛
        tournament_indices = np.random.choice(population.shape[0], tournament_size, replace=False)
        tournament_fitness = sensitivity_fitness_array[tournament_indices]
        # 选择适应度最高的个体
        winner_index = tournament_indices[np.argmin(tournament_fitness)]
        selected_population.append(population[winner_index])
    selected_population_array=np.array(selected_population)
    selected_population=np.concatenate((better_individual_array,selected_population_array),axis=0)
    return selected_population

# # 选择（轮盘赌选择）
# def select(population, sensitivity_fitness_array):
#     if np.max(sensitivity_fitness_array)==np.min(sensitivity_fitness_array):
#         probabilities=np.full_like(np.array(sensitivity_fitness_array), 1 / len(population), dtype=float)
#     else:
#         fitness_values = (np.max(sensitivity_fitness_array)-sensitivity_fitness_array)/ (np.max(sensitivity_fitness_array) - np.min(sensitivity_fitness_array))
#         probabilities =fitness_values/np.sum(fitness_values)
#     selected_index= np.random.choice(population.shape[0], size=len(population), p=probabilities)
#     selected_population=population[selected_index]
#     return selected_population


def ensure_elements_exist(individual,clustered_node_list_1):
    # 检查 array 是否包含 check_list 中的元素
    if not np.isin(individual,clustered_node_list_1).any():
        # 随机替换 array 中的一个元素
        replace_index = np.random.randint(0, len(individual))  # 随机选择一个索引
        new_element = np.random.choice(clustered_node_list_1)  # 从 check_list 中随机选取一个元素
        individual[replace_index] =new_element  # 替换
    return individual


# 交叉（单点交叉）
def crossover(parent1, parent2,clustered_node_list_1):
    child1=parent1.copy()
    child2=parent2.copy()
    if random.random() < 0.9:
        point = np.random.randint(1, len(parent1))
        child1 =np.concatenate((parent1[:point], parent2[point:]))
        child1=ensure_elements_exist(child1,clustered_node_list_1)
        child2 =np.concatenate((parent2[:point], parent1[point:]))
        child2=ensure_elements_exist(child2,clustered_node_list_1)
    return child1, child2
 
# 变异
def mutate(individual,mutation_rate,clustered_node_list_1,clustered_node_list_2):
    child = individual.copy()
    if random.random() < mutation_rate:
        remain_nodes=list(set(clustered_node_list_1+clustered_node_list_2)-set(individual.tolist()))
        replace_node = random.choice(remain_nodes)
        replace_index = np.random.randint(0, len(child))
        child[replace_index]=replace_node
        child=ensure_elements_exist(child,clustered_node_list_1)
    return child


def population_diversity(population):
    population_size = len(population)
    diversity_sum = 0
    for i in range(population_size):
        for j in range(i + 1, population_size):
            intersection_size = len(set(population[i]) & set(population[j]))
            union_size = len(set(population[i]) | set(population[j]))
            jaccard_similarity = intersection_size / union_size
            diversity_sum += jaccard_similarity
    avg_similarity = diversity_sum / (population_size * (population_size - 1) / 2)
    return avg_similarity
 
# 遗传算法主函数
def genetic_algorithm(covariance_matrix_dict,burst_H_decline_dict,clustered_node_list_1, clustered_node_list_2,sensor_num,low_generations,nsga_population_size):
    # 初始化种群
    population_size=500
    population = initialize_population(clustered_node_list_1, clustered_node_list_2,population_size, sensor_num)
    mutation_rate=0.5
    all_gen_best_sensors={}
    best_sensitivity_record=[]
    time_consume_record=[]
    evolve_start_time = time.time()
    for generation in range(low_generations):
        # 评估种群适应度
        sensitivity_fitness_array= parallel_calculate_low_objectives(population,burst_H_decline_dict,covariance_matrix_dict, num_workers=4)
        best_sensitivity_record.append(np.min(sensitivity_fitness_array))
        current_gen_max_sensitivity_index= np.argsort(sensitivity_fitness_array)[:20]
        current_gen_best_sensors= population[current_gen_max_sensitivity_index]
        all_gen_best_sensors[str(generation)]= current_gen_best_sensors
        # 选择
        selected_population = select(population,sensitivity_fitness_array)
        # 生成新种群
        new_population = []
        for i in range(0, len(selected_population), 2):
            parent1 = selected_population[i]
            parent2 = selected_population[i+1]
            child1, child2 = crossover(parent1,parent2,clustered_node_list_1)
            mutated_child1=mutate(child1,mutation_rate,clustered_node_list_1,clustered_node_list_2)
            mutated_child2=mutate(child2,mutation_rate,clustered_node_list_1,clustered_node_list_2)
            new_population.append(mutated_child1)
            new_population.append(mutated_child2)
        selected_new_population=select(new_population, sensitivity_fitness_array, tournament_size=3)
        indices= np.random.choice(np.arange(len(selected_new_population)), population_size-20, replace=False)
        population =np.concatenate((selected_population[:20],selected_new_population[indices]))
        #收敛判断
        unique_population=np.unique(population, axis=0)
        if len(best_sensitivity_record) >= 3:
            recent_diffs = np.abs(np.diff(best_sensitivity_record[-3:]))
            avg_similarity = population_diversity(population)
            if np.max(recent_diffs) <0.01 and len(unique_population)<100:
                print(f"适应度收敛 & 种群相似度高，提前终止进化！")
                break

        current_gen_end_time = time.time()
        all_execution_time = current_gen_end_time - evolve_start_time
        time_consume_record.append(all_execution_time)
    # 返回最佳个体
    unique_population=np.unique(population, axis=0)
    last_gen_sensitivity_results= parallel_calculate_low_objectives(unique_population,burst_H_decline_dict,covariance_matrix_dict, num_workers=4)
    best_sensitivity_record.append(np.min(last_gen_sensitivity_results))
    last_gen_max_sensitivity_index= np.argsort(last_gen_sensitivity_results)[:20]
    last_gen_best_sensors= unique_population[last_gen_max_sensitivity_index]
    all_gen_best_sensors[str(generation+1)]=last_gen_best_sensors
    current_gen_end_time = time.time()
    all_execution_time = current_gen_end_time - evolve_start_time
    time_consume_record.append(all_execution_time)
    max_sensitivity_index= np.argsort(last_gen_sensitivity_results)[:nsga_population_size]
    max_sensitivity=np.sort(last_gen_sensitivity_results)[:nsga_population_size]
    best_sensors_population= unique_population[max_sensitivity_index]
    return best_sensors_population,max_sensitivity,all_gen_best_sensors,time_consume_record,best_sensitivity_record



#case
# if __name__ == "__main__":
#     with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_covariation.pkl", "rb") as f:
#         covariance_matrix_dict= pd.read_pickle(f)
#     with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl", "rb") as f:
#         burst_H_decline_dict= pd.read_pickle(f)
#     clustered_node_list_1=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_divide_a_nodes.xlsx", sheet_name='Sheet1'))['a_index'].tolist()
#     clustered_node_list_1=list(map(int, clustered_node_list_1[0:8]))
#     clustered_node_list_2=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_divide_a_nodes.xlsx", sheet_name='Sheet1'))['other_index'].tolist()
#     population_size=100
#     sensor_num=8
#     low_generations=5
#     best_sensors,max_sensitivity,all_gen_best_sensors,time_consume_record=genetic_algorithm(covariance_matrix_dict,burst_H_decline_dict,clustered_node_list_1, clustered_node_list_2,sensor_num,low_generations)
#     print(best_sensors)
#     print(max_sensitivity)
#     print(all_gen_best_sensors)
#     print(time_consume_record)