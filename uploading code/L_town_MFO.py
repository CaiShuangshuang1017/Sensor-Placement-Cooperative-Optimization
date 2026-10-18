#计算低保真度各代优势个体的高保真度值
import numpy as np
import pandas as pd
import os
import L_town_genetic_sensitivity
import L_town_gain_fitness
import L_town_nsga_gain_better
import multiprocessing
from multiprocessing import Pool
from collections import defaultdict

def calculate_single_objective(individual, fitness_cache,covariance_matrix_dict,burst_H_decline_dict, all_pipe_Qmax_list,all_Q_H_path, sensitivity_threshold):
    """计算单个个体的目标函数值"""
    if tuple(individual) in fitness_cache:
        [cover_ratio, coverage_probability_result]=fitness_cache[tuple(individual)]
    else:
        cover_ratio, coverage_probability_result=L_town_gain_fitness.get_gain_results(individual,all_pipe_Qmax_list,all_Q_H_path,
                                                                                      covariance_matrix_dict,burst_H_decline_dict,sensitivity_threshold)
        
    return [cover_ratio,coverage_probability_result]

def parallel_calculate_objectives(population, fitness_cache, access_count,covariance_matrix_dict,burst_H_decline_dict,
                                  all_pipe_Qmax_list,all_Q_H_path, sensitivity_threshold, num_workers=4):
    """并行计算目标函数值"""
    
    with Pool(processes=num_workers) as pool:
        # 为每个个体分配计算任务
        results= pool.starmap(calculate_single_objective, [(individual, fitness_cache,covariance_matrix_dict,burst_H_decline_dict, 
                                                            all_pipe_Qmax_list,all_Q_H_path, sensitivity_threshold) for individual in population])
    for individual, result in zip(population, results):
        fitness_cache[tuple(individual)]=result  # 先存入字典
        if tuple(individual) in access_count:
            access_count[tuple(individual)] += 1
        else:
            access_count[tuple(individual)] = 1
    fitness_cache=dict(fitness_cache)  
    array_results=np.array(results)
    return array_results,fitness_cache, access_count

def calculate_objectives(population, fitness_cache, access_count,covariance_matrix_dict,
                         burst_H_decline_dict,all_pipe_Qmax_list, all_Q_H_path, sensitivity_threshold) -> np.ndarray:
    """并行计算目标函数值"""
    # 使用多核并行化计算目标函数
    objectives,fitness_cache, access_count= parallel_calculate_objectives(population, fitness_cache, access_count,
                                                                          covariance_matrix_dict,burst_H_decline_dict,
                                                                          all_pipe_Qmax_list, all_Q_H_path, sensitivity_threshold,
                                                                          num_workers=4)  # 使用所有可用的核心)
    return objectives,fitness_cache, access_count

def dominates(obj1: np.ndarray, obj2: np.ndarray) -> bool:
    """判断obj1是否支配obj2"""
    return np.all(obj1 >= obj2) and np.any(obj1 > obj2)

def fast_non_dominated_sort(population: np.ndarray, objectives: np.ndarray):
    """快速非支配排序"""
    n = len(population)
    domination_count = np.zeros(n)
    dominated_solutions = [[] for _ in range(n)]
    fronts = [[]]
    for i in range(n):
        for j in range(i + 1, n):
            if dominates(objectives[i], objectives[j]):
                dominated_solutions[i].append(j)
                domination_count[j] += 1
            elif dominates(objectives[j], objectives[i]):
                dominated_solutions[j].append(i)
                domination_count[i] += 1
    for i in range(n):
        if domination_count[i] == 0:
            fronts[0].append(i)   
    i = 0
    while fronts[i]:
        next_front = []
        for j in fronts[i]:
            for k in dominated_solutions[j]:
                domination_count[k] -= 1
                if domination_count[k] == 0:
                    next_front.append(k)
        i += 1
        fronts.append(next_front)
    return fronts[:-1]

def get_low_process_high_objective(covariance_matrix_dict,burst_H_decline_dict,clustered_node_list_1,clustered_node_list_2,
                                   sensor_num,low_generations,all_pipe_Qmax_list,all_Q_H_path,sensitivity_threshold,nsga_population_size):
    best_sensors,max_sensitivity,all_gen_best_sensors,time_consume_record,best_sensitivity_record=L_town_genetic_sensitivity.genetic_algorithm(covariance_matrix_dict,burst_H_decline_dict,
                                                                                                                       clustered_node_list_1,clustered_node_list_2,
                                                                                                                       sensor_num,low_generations,nsga_population_size)
    fitness_cache={}
    access_count={}
    all_gen_high_fitness_evolve=[]
    for gen in range(len(all_gen_best_sensors)):
        current_gen_best_sensors=all_gen_best_sensors[str(gen)]
        objectives,fitness_cache,access_count=calculate_objectives(current_gen_best_sensors,fitness_cache,access_count,covariance_matrix_dict,
                                                                   burst_H_decline_dict,all_pipe_Qmax_list,all_Q_H_path,sensitivity_threshold)
        # 非支配排序
        fronts = fast_non_dominated_sort(current_gen_best_sensors, objectives)
        #current_gen_front_0=current_gen_best_sensors[fronts[0]]#最优个体基因
        pareto_front = np.array([objectives[i] for i in fronts[0]])  # 取非支配解
        #去除重复帕累托前沿个体
        unique_pareto_front=np.unique(pareto_front, axis=0)
        best_fitness_1 = np.mean(unique_pareto_front[:, 0])  # 目标 1 的均值
        best_fitness_2 = np.mean(unique_pareto_front[:, 1])  # 目标 2 的均值
        all_gen_high_fitness_evolve.append([best_fitness_1,best_fitness_2])
    all_gen_high_fitness_evolve_array=np.array(all_gen_high_fitness_evolve)
    return best_sensors,all_gen_high_fitness_evolve_array,time_consume_record,best_sensitivity_record

if __name__ == "__main__":
    for run in range(6,11):
        num=8
        ######
        #m_noise='m_0.6'
        global pool  
        num_workers = max(1, os.cpu_count() // 2)  # 限制 CPU 资源
        pool = Pool(num_workers)  # 初始化进程池
        reset_every_n_generations=1
        nsga2=L_town_nsga_gain_better.NSGA2(sensor_num=num)
        covariance_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_covariation.pkl"
        with open(covariance_path, "rb") as f:
            covariance_matrix_dict= pd.read_pickle(f)
        H_decline_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data.pkl"
        with open(H_decline_path,"rb") as f:
            burst_H_decline_dict= pd.read_pickle(f)
        clustered_node_list_1=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_divide_a_nodes.xlsx", sheet_name='Sheet1'))['a_index'].tolist()
        clustered_node_list_1=list(map(int, clustered_node_list_1[0:8]))
        clustered_node_list_2=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_divide_a_nodes.xlsx", sheet_name='Sheet1'))['other_index'].tolist()
        sensor_num=num
        low_generations=10
        nsga_population_size=100
        all_pipe_Qmax_list=(pd.read_excel(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_pipes_Qmax.xlsx", sheet_name='Sheet1'))['Qmax'].tolist()
        all_Q_H_path=r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证"
        sensitivity_threshold=-4.22068293050037
        ####低保真度优化####
        best_sensors_population,all_gen_high_fitness_evolve_array,time_consume_record,best_sensitivity_record=get_low_process_high_objective(covariance_matrix_dict,burst_H_decline_dict,
                                                                                                                        clustered_node_list_1,clustered_node_list_2,
                                                                                                                        sensor_num,low_generations,all_pipe_Qmax_list,
                                                                                                                        all_Q_H_path,sensitivity_threshold,nsga_population_size)
        genetic_evolve_process_results= np.hstack((all_gen_high_fitness_evolve_array,np.array(time_consume_record).reshape(-1, 1)))
        #####高保真度优化#######
        final_population,fitness_cache,access_count,all_gen_best_fitness_matrix,nsga_time_consume_record,unique_current_gen_front_0,unique_fitness=nsga2.evolve(best_sensors_population)
        pareto_result = np.hstack((unique_current_gen_front_0, unique_fitness))
        print(pareto_result)
        df = pd.DataFrame(pareto_result)
        file_path =os.path.join(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\算法不确定性", f"MFO_result_{run}.xlsx")
        df.to_excel(file_path, index=False, header=False)
        print(f"最优数据已成功写入 {file_path}")
        pool.close()
        pool.join()
    #nsga_evolve_process_results= np.hstack((all_gen_best_fitness_matrix,np.array(nsga_time_consume_record).reshape(-1, 1)))
    # ####保存迭代收敛过程数据
    # all_evolve_results= np.vstack((genetic_evolve_process_results,nsga_evolve_process_results))
    # evolve_results_df=pd.DataFrame(all_evolve_results)
    # evolve_file_path = os.path.join(r"D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\参数不确定性分析\COP", f"genetic_evolve_{m_noise}_2.xlsx")
    # evolve_results_df.to_excel(evolve_file_path, index=False, header=False)
    # print(f"迭代数据已成功写入 {evolve_file_path}")
    #unique_final_objectives,fitness_cache, access_count= nsga2.calculate_objectives(unique_final_population, fitness_cache, access_count)
    #print(unique_final_objectives)
    # 计算最终种群的目标值
    #final_objectives = nsga2.calculate_objectives(final_population)
    # 绘制帕累托前沿
    # import matplotlib.pyplot as plt
    # plt.figure(figsize=(10, 6))
    # plt.scatter(unique_fitness[:, 0], unique_fitness[:, 1])
    # plt.xlabel('f1')
    # plt.ylabel('f2')
    # plt.title('Pareto Front')
    # plt.grid(True)
    # plt.show()