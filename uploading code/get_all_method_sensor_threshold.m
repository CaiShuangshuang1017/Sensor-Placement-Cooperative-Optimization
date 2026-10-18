%%%求各种传感器方案中各传感器报警阈值
clear;
clc;

node_std=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\参数不确定性分析\all_noise_time_mean_std\L_town_all_time_mean_std_d_0.8.xlsx",'std','A1:X785');
current_sensors=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\参数不确定性分析\Du_all_noise_selected_sensors - 副本 (2).xlsx",'d_0.8','B3:B10');

%MCS
% sensor_num=4;
% cluster_nodes=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_clustered_nodes.xlsx",'Sheet1','B2:B101');
% current_sensors= randsample(cluster_nodes,sensor_num);

current_sensor_std=node_std(current_sensors, :);
current_sensor_threshold= current_sensor_std.*-2.575829303548901;