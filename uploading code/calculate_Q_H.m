%%%%获取各管的爆管流量压降表
clear;
clc;

%%%读取管段信息
pipe_info= readtable("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\burst_pipe_inform.xlsx",'Range','A2:P907','ReadRowNames',false);
%%%读取节点压力均值
node_mean_pressure=xlsread("D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\base_all_nodes_1h_normal_data.xlsx",'sheet1','C2:C783');
Q_H_folder = "D:\A_科研相关\小论文2_合作监测点布置\覆盖双目标优化\L-town模拟验证\L_town_burst_Q_H_1h"; % 指定文件夹名称
if ~exist(Q_H_folder, 'dir')  % 如果文件夹不存在，则创建
    mkdir(Q_H_folder);
end

%%%%%%%%模拟爆管
tic
for i=162:400
    disp(i);
    T_H=[];
    All_P_decline=[];
    current_pipe_header=[];
    %%%本轮原管段信息
    pipe_index=table2array(pipe_info(i,1));%本轮管段index
    pipe_id=cell2mat(table2array(pipe_info(i,2)));
    pipe_id=pipe_id(1:end-1);%本轮管段id
    pipe_length=table2array(pipe_info(i,3));%本轮管段长度
    pipe_diam=table2array(pipe_info(i,4));%本轮管段直径
    pipe_rough=table2array(pipe_info(i,5));%本轮管段粗糙系数

    node1_id=cell2mat(table2array(pipe_info(i,7)));%本轮管段相连节点信息id，x，y，h
    node1_id=node1_id(1:end-1);
    node2_id=cell2mat(table2array(pipe_info(i,12)));
    node2_id=node2_id(1:end-1);
    co_node_x1=table2array(pipe_info(i,9));
    co_node_x2=table2array(pipe_info(i,14));
    co_node_y1=table2array(pipe_info(i,10));
    co_node_y2=table2array(pipe_info(i,15));
    co_node_elev1=table2array(pipe_info(i,8));
    co_node_elev2=table2array(pipe_info(i,13));

    pipe_Qmax=table2array(pipe_info(i,16));
    step=pipe_Qmax/250;
    
    for burst_flow=0:step:pipe_Qmax
        current_pipe_header=[current_pipe_header,burst_flow];
        %%%重新载入原未变管网
        start_toolkit;
        wds = epanet('L-TOWN.inp');
        node_num=wds.getNodeCount;

        %%%删除本轮原管段
        wds.deleteLink(pipe_index);
        %%%新增1个节点NJ1【两个节点是完全断管】
        junctionID = 'NJ1';
        nj1_x=(co_node_x1+co_node_x2)/2;
        nj1_y=(co_node_y1+co_node_y2)/2;
        junctionCoords = [nj1_x,nj1_y];
        nj1_elev=(co_node_elev1+co_node_elev2)/2;
        junctionElevation =nj1_elev;
        demand =burst_flow;
        nj1_index=wds.addNodeJunction(junctionID, junctionCoords, junctionElevation, demand);

        %%%新增两根管段NP1，NP2
        pipeID = 'NP1';
        fromNode = node1_id;
        toNode = 'NJ1';
        length = pipe_length/2;
        diameter =pipe_diam;
        roughness = pipe_rough;
        np1_index=wds.addLinkPipe(pipeID, fromNode, toNode, length, diameter, roughness);

        pipeID = 'NP2';
        fromNode = node2_id;
        toNode = 'NJ1';
        length = pipe_length/2;
        diameter =pipe_diam;
        roughness = pipe_rough;
        np2_index= wds.addLinkPipe(pipeID, fromNode, toNode, length, diameter, roughness);

        %%%设置PDA
        type = 'PDA';
        pmin = 5;
        preq = 18;
        pexp = 0.5;
        wds.setDemandModel(type, pmin, preq, pexp);
        demandmodel_now=wds.getDemandModel;


        %%%%%水力分析,计算各监测点压力值、Qmax，记录
        hrs =1;%168
        wds.setTimeSimulationDuration(hrs*3600);
        wds.openHydraulicAnalysis;
        wds.initializeHydraulicAnalysis;
        wds.runHydraulicAnalysis;
        tstep=1;
        while (tstep>0)
            t=wds.runHydraulicAnalysis;
            if t>0 && fix(t/3600)==hrs && mod(t,3600)==0
                disp(t);
                current_P=wds.getNodePressure;
                current_P=current_P';
                current_P=current_P(1:782);
                current_P_decline=current_P-node_mean_pressure;
                All_P_decline=[All_P_decline,current_P_decline];
            end
            T_H=[T_H; t];
            tstep=wds.nextHydraulicAnalysisStep;
        end
        wds.closeHydraulicAnalysis;
        %%%结束本轮计算，卸载已变管网
        wds.unload;
        toc
    end
    modified_P_decline=[current_pipe_header;All_P_decline];
    n_rows=size(modified_P_decline, 1);  % 获取矩阵 A 的行数
    hanghao=(0:n_rows-1)';
    modified_P_decline=[hanghao,modified_P_decline];
    current_csv_path=fullfile(Q_H_folder, sprintf('p_%d_burst_Q_H.csv', i));
    xlswrite(current_csv_path, modified_P_decline);
end