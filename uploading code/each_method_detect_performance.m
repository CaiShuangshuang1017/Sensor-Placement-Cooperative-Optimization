%%%计算不同布置方案对爆管的检测率
clear;
clc;

% load("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\参数不确定性分析\all_noise_10000_burst_event\all_burst_10000_d_0.8.mat")
% load("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\参数不确定性分析\all_noise_10000_normal_event\all_normal_10000_d_0.8.mat")
% all_burst_data=all_burst_data_results;
% all_noraml_data=all_normal_data_results;
load("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_burst_all_time.mat")
load("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_normal_all_time.mat")
all_burst_data=all_10000_burst_all_time;
all_noraml_data=all_10000_normal_all_time;
% all_burst_data=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_detailed_burst_data.xlsx",'Sheet1','A2:ADE10001');
% all_noraml_data=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_normal_data.xlsx",'Sheet1','A2:ADC10001');
current_sensor=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_method_different_sensor_num\all_method_selected_sensors_8.xlsx",'du','B3:B10');
sensor_threshold=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_method_different_sensor_num\all_method_selected_sensors_8.xlsx",'du','C3:Z10');

all_burst_time=all_burst_data(:,3);
all_normal_time=all_noraml_data(:,1);
current_sensor_burst_decline=all_burst_data(:,current_sensor);
current_sensor_normal_decline=all_noraml_data(:,current_sensor);
detect_num=0;
false_num=0;
detect_list=zeros(10000,1);
for i=1:10000
    current_burst_time=all_burst_time(i);
    current_burst_time_threshold=sensor_threshold(:,current_burst_time);
    current_burst_decline=current_sensor_burst_decline(i,:)';
    if any(current_burst_decline<current_burst_time_threshold)
        detect_num=detect_num+1;
        detect_list(i)=1;
    end
    current_normal_time=all_normal_time(i);
    current_normal_time_threshold=sensor_threshold(:,current_normal_time);
    current_normal_decline=current_sensor_normal_decline(i,:)';
    if any(current_normal_decline<current_normal_time_threshold)
        false_num=false_num+1;
    end
end
detect_ratio=detect_num/10000;
false_ratio=false_num/10000;