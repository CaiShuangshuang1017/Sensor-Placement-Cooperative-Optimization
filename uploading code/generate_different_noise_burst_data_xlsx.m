%生成不同噪声条件的base_all_nodes_1/4/10_burst_data.xlsx

clear;
clc;



original_burst_data_xlsx=readtable("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_node_burst_data\base_all_nodes_10h_burst_data.xlsx",'Range','A1:AHZ783','ReadRowNames',false, 'ReadVariableNames', true, 'PreserveVariableNames', true);
hr=10;
tic;
for measure_noise_std=0.3:0.1:0.8

    start_toolkit;
    wds = epanet('L-TOWN.inp');
    demand_type=wds.getDemandModel;
    type='PDA';
    pmin=5;
    preq=18;
    pexp=0.5;

    wds.setDemandModel(type, pmin, preq, pexp);
    demand_type=wds.getDemandModel;
    node_basedemand=[];

    node_num=wds.getNodeCount;
    node_id=wds.getNodeNameID;
    for i=1:node_num
        node_basedemand=[node_basedemand;cell2mat(wds.getNodeBaseDemands(i))];
    end
    T_H=[];
    All_P=[];
    itera_num=200;%蒙特卡洛模拟次数
    for itera=1:itera_num
        disp(itera);
        %%修改需水量
        for i=1:node_num-3
            for j=1:3
                current_category_basedemand=node_basedemand(i,j);
                if current_category_basedemand>10000
                    current_category_basedemand_new=normrnd(current_category_basedemand,current_category_basedemand*0);
                else
                    current_category_basedemand_new=normrnd(current_category_basedemand,current_category_basedemand*0.2);
                end
                wds.setNodeBaseDemands(i,j,current_category_basedemand_new);
            end
        end
        basedemands_new=wds.getNodeBaseDemands(1);
        %%%水力分析
        hrs =hr;%输入几个小时就是几点
        wds.setTimeSimulationDuration(hrs*3600);
        wds.openHydraulicAnalysis;
        wds.initializeHydraulicAnalysis;
        wds.runHydraulicAnalysis;
        tstep=1;
        while (tstep>0)
            t=wds.runHydraulicAnalysis;
            if t>=0 & fix(t/3600)==hrs & mod(t,3600)==0
                demand_all=wds.getNodeActualDemand;
                current_P=wds.getNodePressure;
                current_P=current_P';
                All_P=[All_P,current_P];
            end
            T_H=[T_H; t];
            tstep=wds.nextHydraulicAnalysisStep;
        end
        wds.closeHydraulicAnalysis;
    end


    %%%给计算值赋测量噪声
    measure_noise=normrnd(0,measure_noise_std, size(All_P));
    All_P_actual=All_P+measure_noise;
    All_P_mean=mean(All_P_actual,2);
    All_P_std = std(All_P_actual, 0, 2);
    All_P_threshold=-4.22068293050037*std(All_P_actual, 0, 2);
    original_burst_data_xlsx.('mean')=All_P_mean(1:782);
    original_burst_data_xlsx.('std')=All_P_std(1:782);
    original_burst_data_xlsx.('threshold_5%_0.5%')=All_P_threshold(1:782);
    filepath = fullfile("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\", sprintf('%s_%s_%s%s', 'base_all_nodes_burst_data_m',num2str(measure_noise_std),num2str(hr),".xlsx"));
    writetable(original_burst_data_xlsx, filepath);
    %%%结束本轮计算，卸载已变管网
    wds.unload;
    toc;
end
