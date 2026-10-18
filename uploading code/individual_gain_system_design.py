import numpy as np
import pandas as pd
import random
from openpyxl import load_workbook
from collections import Counter
from collections import Counter

# 初始化种群
def initialize_population(population_size, sensor_num):
    population =np.random.randint(0, 2, (population_size, sensor_num))
    return population

# population_size=100
# sensor_num=8
# population=initialize_population(population_size, sensor_num)
# print(population)

# population=np.array([[0,0,0,0,0],[0,1,0,0,0],[1,1,1,0,0]])
# covariance_matrix=np.array([
#     [4, 2, 0.6, 0.5, 0.3],
#     [2, 3, 0.5, 0.2, 0.1],
#     [0.6, 0.5, 2, 0.1, 0.2],
#     [0.5, 0.2, 0.1, 1, 0.3],
#     [0.3, 0.1, 0.2, 0.3, 1]])
# pipe_burst_matrix=np.array([-1,-2,-3,-4,-5])

#适应度评估
def evaluate_population(population,covariance_matrix,pipe_burst_matrix):
    var_matrix =population@ covariance_matrix @ population.T
    std_results = np.sqrt(np.diag(var_matrix))
    H_decline_results=population@pipe_burst_matrix
    sensitivity_results= np.divide(H_decline_results,np.where(std_results==0, np.inf, std_results))
    return sensitivity_results



# sensitivity_results=evaluate_population(population,covariance_matrix,pipe_burst_matrix)
# print(sensitivity_results)

# population=np.array([[0,0,0,0,0],[0,1,0,0,0],[1,1,1,0,0]])
# sensitivity_results=np.array([-0.1,-0.5,-3])
# 选择（轮盘赌选择）
def select(population, sensitivity_results):
    if np.max(sensitivity_results)==np.min(sensitivity_results):
        probabilities=np.full_like(np.array(sensitivity_results), 1 / len(population), dtype=float)
    else:
        fitness_values = (np.max(sensitivity_results)-sensitivity_results)/ (np.max(sensitivity_results) - np.min(sensitivity_results))
        probabilities =fitness_values/np.sum(fitness_values)
    selected_index= np.random.choice(population.shape[0], size=len(population), p=probabilities)
    selected_population=population[selected_index]
    return selected_population

# selected_population=select(population, sensitivity_results)
# print(selected_population)

# 交叉（单点交叉）
def crossover(parent1, parent2):
    point = np.random.randint(1, len(parent1))
    child1 =np.concatenate((parent1[:point], parent2[point:]))
    child2 =np.concatenate((parent2[:point], parent1[point:]))
    return child1, child2
 
# 变异
def mutate(individual, mutation_rate):
    if random.random() < mutation_rate:
        gene_index = np.random.randint(0, individual.shape[0])
        individual[gene_index]=1-individual[gene_index]
    return individual

# individual=np.array(([0,1,0,0,0]))
# mutation_rate=1
# individual=mutate(individual, mutation_rate)
# print(individual)
 
# 遗传算法主函数
def genetic_algorithm(covariance_matrix,pipe_burst_matrix, population_size, sensor_num, generations, mutation_rate):
    # 初始化种群
    population = initialize_population(population_size, sensor_num)
    best_combination = None
    best_sensitivity = float('inf')
    no_improve_rounds = 0  # 连续未改进轮数
    for generation in range(generations):
        # 评估种群适应度
        sensitivity_results= evaluate_population(population,covariance_matrix,pipe_burst_matrix)
        # 获取当前最优个体
        gen_best_index = np.argmin(sensitivity_results)
        gen_best_sensitivity = sensitivity_results[gen_best_index]
        gen_best_individual = population[gen_best_index]
        # 精英保留更新
        if gen_best_sensitivity < best_sensitivity - 0.0001:
            best_sensitivity = gen_best_sensitivity
            best_combination = gen_best_individual.copy()
            no_improve_rounds = 0
        else:
            no_improve_rounds += 1

        if no_improve_rounds >= 5:
            #print(f"增益设计早收敛停于第 {generation} 代")
            break
        # 选择
        selected_population = select(population, sensitivity_results)
        # 生成新种群
        new_population = []
        for i in range(0, len(selected_population), 2):
            parent1 = selected_population[i]
            parent2 = selected_population[i+1]
            child1, child2 = crossover(parent1, parent2)
            new_population.append(mutate(child1, mutation_rate))
            new_population.append(mutate(child2, mutation_rate))
        worst_idx = np.argmax(evaluate_population(np.array(new_population), covariance_matrix, pipe_burst_matrix))
        new_population[worst_idx] = best_combination.copy()
        population = np.array(new_population)
    # 返回最佳个体
    last_gen_sensitivity_results= evaluate_population(population,covariance_matrix,pipe_burst_matrix)
    max_sensitivity_index= np.argmin(last_gen_sensitivity_results)
    max_sensitivity=np.min(last_gen_sensitivity_results)
    best_combination= population[max_sensitivity_index]
    return best_combination,max_sensitivity


def design_gain_system(current_individual_index,covariance_matrix_array,pipe_burst_matrix_array, population_size,generations, mutation_rate,sensitivity_threshold):
    physical_sensor_num=len(current_individual_index)
    current_sub_covariance_array=covariance_matrix_array[np.ix_(current_individual_index,current_individual_index)]
    all_pipe_best_combination=[]
    all_pipe_best_sensitivity=[]
    pipe_num=pipe_burst_matrix_array.shape[0]
    for pipe_index in range(0,pipe_num):
        #print(pipe_index)
        current_sub_burst_array=(pipe_burst_matrix_array[np.ix_([pipe_index], current_individual_index)]).flatten()
        best_combination,max_sensitivity=genetic_algorithm(current_sub_covariance_array,current_sub_burst_array, population_size, physical_sensor_num, generations, mutation_rate)
        all_pipe_best_combination.append(best_combination)
        all_pipe_best_sensitivity.append(max_sensitivity)
    # counter = Counter(tuple(c) for c in all_pipe_best_combination)
    # threshold = 1
    # frequent_combinations_with_count = [(comb, count) for comb, count in counter.items() if count >threshold]
    # print(frequent_combinations_with_count)
    # frequent_combinations = [comb for comb, count in counter.items() if count >threshold]
    #unique_combinations= list({tuple(combination) for combination in all_pipe_best_combination})
    # 重新转换回 NumPy 数组
    selected_combinations= [np.array(combination) for combination in all_pipe_best_combination]
    filtered_selected_combinations= [combination for combination in selected_combinations if not np.all(combination== 0)]
    selected_combinations_var_matrix =np.array(filtered_selected_combinations)@ current_sub_covariance_array @ (np.array(filtered_selected_combinations).T)
    selected_combinations_std_results = np.sqrt(np.diag(selected_combinations_var_matrix))
    selected_combinations_threshold= selected_combinations_std_results*sensitivity_threshold
    #gain_system_combinations= [[val for mask, val in zip(row, current_individual_index) if mask == 1] for row in filtered_selected_combinations]
    filtered_selected_combinations = np.array(filtered_selected_combinations)  # 保证是 numpy 数组
    current_individual=[x + 1 for x in current_individual_index]
    current_individual = np.array(current_individual)  # 保证是 numpy 数组
    gain_system_combinations = [current_individual[row.astype(bool)].tolist() for row in filtered_selected_combinations]
    #求覆盖率
    cover_list =[1 if val < sensitivity_threshold else 0 for val in all_pipe_best_sensitivity]
    coverage_ratio=np.sum(np.array(all_pipe_best_sensitivity)<sensitivity_threshold)/len(all_pipe_best_sensitivity)
    return gain_system_combinations,selected_combinations_threshold,coverage_ratio,cover_list

#case
with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_covariation.pkl", "rb") as f:
    covariance_matrix_dict= pd.read_pickle(f)

with open(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl", "rb") as f:
    burst_H_decline_dict= pd.read_pickle(f)

population_size=100
generations=100
mutation_rate=0.2


current_individual=[347,203,268,516,252,74,397,50]

current_individual_index=[x - 1 for x in current_individual]
sensitivity_threshold=-4.22068293050037
time_list=['1h','4h','10h']
all_time_combination={}
for time_index in range(0,3):
    current_time=time_list[time_index]
    covariance_matrix=covariance_matrix_dict[f"covariation_{current_time}.xlsx"]
    covariance_matrix_array=(covariance_matrix.iloc[:,-782:]).to_numpy()
    pipe_burst_matrix=burst_H_decline_dict[f"base_all_nodes_{current_time}_burst_data.xlsx"]
    pipe_burst_matrix_array=(pipe_burst_matrix.iloc[:,-905:]).to_numpy()
    pipe_burst_matrix_array=pipe_burst_matrix_array.T
    gain_system_combinations,gain_system_threshold,coverage_ratio,cover_list=design_gain_system(current_individual_index,covariance_matrix_array,pipe_burst_matrix_array, 
                                                                                    population_size, generations, mutation_rate,sensitivity_threshold)
    all_time_combination[current_time]=gain_system_combinations



result = []

for list_of_lists in all_time_combination.values():
    result.extend(list_of_lists)



# 统计每个组合出现次数
all_counter = Counter(tuple(c) for c in result)
for selected_virtual_num in range(5,30):
    top_combinations = [comb for comb, count in all_counter.most_common(selected_virtual_num)]
    unique_result = list(map(list, top_combinations))
    unique_result.sort(key=len)

    print(unique_result)


    #求不同组合的报警阈值
    all_hr_lists = []
    for hr in range(1,25):
        current_hr_df = pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\L_town_all_time_P_actual.xlsx", sheet_name=str(hr))
        current_hr_threshold=[]
        for combination in unique_result:
            sum_row =current_hr_df.loc[[x - 1 for x in combination]].sum()
            std_value = np.std(sum_row)
            threshold=-2.575829303548901*std_value
            current_hr_threshold.append(threshold)
        all_hr_lists.append(current_hr_threshold)
    matrix = np.column_stack(all_hr_lists)

    max_len = max(len(sublist) for sublist in unique_result)
    padded_list = [sublist + [np.nan]*(max_len - len(sublist)) for sublist in unique_result]
    array1 = np.array(padded_list)

    combined = np.hstack((array1, matrix))

    df = pd.DataFrame(combined)

    # 写入 xlsx
    file_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\系统误报率控制\selected_virtual_num.xlsx"
    # 加载 workbook
    try:
        book = load_workbook(file_path)
    except FileNotFoundError:
        book = None  # 如果文件不存在，会新建

    # 使用 ExcelWriter 并关联已有 book
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a' if book else 'w') as writer:
        if book:
            writer._book = book  # 注意这里是 _book 而不是 book
        df.to_excel(writer, sheet_name=f'selected_num_{selected_virtual_num}', index=False)

