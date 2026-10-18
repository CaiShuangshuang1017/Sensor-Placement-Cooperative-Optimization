%%%计算不同增益系统对爆管的检测率
clear;
clc;

load("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_burst_all_time.mat")
load("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_normal_all_time.mat")
all_burst_data=all_10000_burst_all_time;
all_noraml_data=all_10000_normal_all_time;
% all_burst_data=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_detailed_burst_data.xlsx",'Sheet1','A2:ADE10001');
% all_noraml_data=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_10000_normal_data.xlsx",'Sheet1','A2:ADC10001');
%current_physical_sensor=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\all_method_different_sensor_num\all_method_selected_sensors_12.xlsx",'gain','B3:B14');
current_gain_sensor=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\系统误报率控制\selected_virtual_num.xlsx",'selected_num_20','A2:G21');
gain_sensor_threshold=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\系统误报率控制\selected_virtual_num.xlsx",'selected_num_20','H2:AE21');

all_burst_time=all_burst_data(:,3);
all_normal_time=all_noraml_data(:,1);

detect_num=0;
false_num=0;
detect_list=zeros(10000,1);
[m, ~] = size(current_gain_sensor);  % A的行数
for i=1:10000
    %disp(i);
    current_burst_time=all_burst_time(i);
    current_burst_time_threshold=gain_sensor_threshold(:,current_burst_time);
    current_burst_decline=all_burst_data(i,4:785);
    %提取当前爆管场景对应的增益传感器压降
    gain_burst_result = zeros(m,1);  % 存放每行的求和结果
    for gain_num = 1:m
        idx = current_gain_sensor(gain_num, :);
        idx = idx(~isnan(idx));
        if ~isempty(idx)
            % 从B中提取第i行的对应列
            extracted =current_burst_decline(1,idx);
            % 求和
            gain_burst_result(gain_num) = sum(extracted);
        end
    end

    if any(gain_burst_result<current_burst_time_threshold)
        detect_num=detect_num+1;
        detect_list(i)=1;
    end
    
    current_normal_time=all_normal_time(i);
    current_normal_time_threshold=gain_sensor_threshold(:,current_normal_time);
    current_normal_decline=all_noraml_data(i,2:783);
    %提取当前场景对应的增益传感器压降
    gain_norm_result = zeros(m,1);  % 存放每行的求和结果
    for gain_num = 1:m
        idx = current_gain_sensor(gain_num, :);
        idx = idx(~isnan(idx));
        if ~isempty(idx)
            extracted =current_normal_decline(1,idx);
            gain_norm_result(gain_num) = sum(extracted);
        end
    end
    if any(gain_norm_result<current_normal_time_threshold)
        false_num=false_num+1;
    end
end
detect_ratio=detect_num/10000;
false_ratio=false_num/10000;