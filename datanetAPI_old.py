"""
Shim to re-export the parent datanetAPI module so this exec folder doesn't shadow the real implementation.
"""
import importlib.util
import os



class DatanetAPI:
    """
    Class containing all the functionalities to read the dataset line by line
    by means of an iteratos, and generate a Sample instance with the
    information gathered.
    """

    def __init__(self, data_folder, intensity_values=None):
        """
        Initialization of the PasringTool instance

        Parameters
        ----------
        data_folder : str
            Folder where the dataset is stored.
        dict_queue : Queue
            Auxiliar data structures used to conveniently move information
            between the file where they are read, and the matrix where they
            are located.
        intensity_values : int or array [x, y]
            User-defined intensity values used to constrain the reading process
            to these/this value/range of values.

        Returns
        -------
        None.

        """

        if intensity_values is None:
            intensity_values = []
        self.data_folder = data_folder
        self.dict_queue = queue.Queue()
        self.intensity_values = intensity_values

    def _readRoutingFile(self, routing_fd, netSize):
        """
        Pending to compare against getSrcPortDst

        Parameters
        ----------
        routing_file : str
            File where the routing information is located.
        netSize : int
            Number of nodes in the network.

        Returns
        -------
        R : netSize x netSize matrix
            Matrix where each  [i,j] states what port node i should use to
            reach node j.

        """

        R = numpy.zeros((netSize, netSize)) - 1
        src = 0
        for line in routing_fd:
            line = line.decode()
            camps = line.split(',')
            dst = 0
            for port in camps[:-1]:
                R[src][dst] = port
                dst += 1
            src += 1
        return (R)

    def _getRoutingSrcPortDst(self, G):
        """
        Return a dictionary of dictionaries with the format:
        node_port_dst[node][port] = next_node

        Parameters
        ----------
        G : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """

        node_port_dst = {}
        for node in G:
            port_dst = {}
            node_port_dst[node] = port_dst
            for destination in G[node].keys():
                port = G[node][destination][0]['port']
                node_port_dst[node][port] = destination
        return node_port_dst

    def _create_routing_matrix(self, G, routing_file):
        """

        Parameters
        ----------
        G : graph
            Graph representing the network.
        routing_file : str
            File where the information about routing is located.

        Returns
        -------
        MatrixPath : NxN Matrix
            Matrix where each cell [i,j] contains the path to go from node
            i to node j.

        """

        netSize = G.number_of_nodes()
        node_port_dst = self._getRoutingSrcPortDst(G)
        R = self._readRoutingFile(routing_file, netSize)
        MatrixPath = numpy.empty((netSize, netSize), dtype=object)
        for src in range(0, netSize):
            for dst in range(0, netSize):
                node = src
                path = [node]
                while R[node][dst] != -1:
                    out_port = R[node][dst]
                    next_node = node_port_dst[node][out_port]
                    path.append(next_node)
                    node = next_node
                MatrixPath[src][dst] = path
        return MatrixPath

    def _get_graph_for_tarfile(self, tar):
        """
    

        Parameters
        ----------
        tar : str
            tar file where the graph file is located.

        Returns
        -------
        ret : graph
            Graph representation of the network.

        """

        for member in tar.getmembers():
            if 'graph' in member.name:
                f = tar.extractfile(member)
                ret = networkx.read_gml(f, destringizer=int)
                return ret

    def _check_intensity(self, file):
        """
    

        Parameters
        ----------
        file : str
            Name of the data file that needs to be filtered by intensity.

        Returns
        -------
        2 if the range of intensities treates in the file satisfies the needs
        of the user.
        1 if there may be lines in the file that do not fulfill the user
        requirements.
        0 if the file does not fulfill the user-defined intensity requirements.

        """

        aux = file.split('_')
        aux = aux[2]
        aux = aux.split('-')
        aux = list(map(int, aux))
        #        User introduced range of intensities
        if len(self.intensity_values) > 1:
            if len(aux) > 1:
                if (aux[0] >= self.intensity_values[0]) and (aux[1] <= self.intensity_values[1]):
                    return 2
                elif (aux[0] > self.intensity_values[1]) or (self.intensity_values[0] > aux[1]):
                    return 0
                else:
                    return 1

            else:
                if self.intensity_values[0] <= aux[0] <= self.intensity_values[1]:
                    return 2
                else:
                    return 0
        #        User introduced single intensity
        elif len(self.intensity_values) == 1:
            if len(aux) == 1 and self.intensity_values[0] == aux[0]:
                return 2
            return 0
        else:
            return 2

    def __process_params_file(self, params_file):
        simParameters = {}
        for line in params_file:
            line = line.decode()
            if "simulationDuration" in line:
                ptr = line.find("=")
                simulation_time = int(line[ptr + 1:])
                simParameters["simulationTime"] = simulation_time
                continue
            if "lambda" in line:
                ptr = line.find("=")
                avgLambdaMax = float(line[ptr + 1:])
                simParameters["avgLambdaMax"] = avgLambdaMax
        return simParameters

    def __process_graph(self, G):
        netSize = G.number_of_nodes()
        for src in range(netSize):
            for dst in range(netSize):
                if dst not in G[src]:
                    continue
                bw = G[src][dst][0]['bandwidth']
                bw = bw.replace("kbps", "000")
                G[src][dst][0]['bandwidth'] = bw

    def __iter__(self):
        """
    

        Yields
        ------
        s : Sample
            Sample instance containing information about the last line read
            from the dataset.

        """

        g = None
        graph_file = False
        s_dirs = []
        for root, dirs, files in os.walk(self.data_folder):
            if "graph_attr.txt" in files:
                g = networkx.read_gml(os.path.join(root, "graph_attr.txt"), destringizer=int)
                graph_file = True
            else:
                s_dir = root.replace(self.data_folder, '')
                if s_dir != '':
                    s_dirs.append(root.replace(self.data_folder, ''))
                continue
            self.__process_graph(g)
            tar_files = [f for f in files if f.endswith("tar.gz")]
            random.shuffle(tar_files)
            for file in tar_files:
                if len(self.intensity_values) == 0:
                    feasibility_of_file = 2
                else:
                    feasibility_of_file = self._check_intensity(file)

                if feasibility_of_file != 0:
                    tar = tarfile.open(os.path.join(root, file), 'r:gz')
                    dir_info = tar.next()
                    routing_file = tar.extractfile(dir_info.name + "/Routing.txt")
                    results_file = tar.extractfile(dir_info.name + "/simulationResults.txt")
                    if dir_info.name + "/flowSimulationResults.txt" in tar.getnames():
                        flowresults_file = tar.extractfile(dir_info.name + "/flowSimulationResults.txt")
                    else:
                        flowresults_file = None
                    params_file = tar.extractfile(dir_info.name + "/params.ini")
                    simParameters = self.__process_params_file(params_file)

                    routing_matrix = self._create_routing_matrix(g, routing_file)
                    while True:
                        s = Sample()
                        s._set_data_set_file_name(os.path.join(root, file))

                        s._results_line = results_file.readline().decode()[:-2]
                        if flowresults_file:
                            s._flowresults_line = flowresults_file.readline().decode()[:-2]
                        else:
                            s._flowresults_line = None

                        if len(s._results_line) == 0:
                            break

                        self._process_flow_results_traffic_line(s._results_line, s._flowresults_line, simParameters, s)
                        s._set_routing_matrix(routing_matrix)
                        s._set_topology_object(g)
                        yield s
        if not graph_file:
            print('ERROR: The API was not able to find the graph information file in any of the following dirs {}.'
                    .format(s_dirs))

    def _process_flow_results_traffic_line(self, rline, fline, simParameters, s):
        """
    

        Parameters
        ----------
        rline : str
            Last line read in the results file.
        fline : str
            Last line read in the flows file.
        s : Sample
            Instance of Sample associated with the current iteration.

        Returns
        -------
        None.

        """

        sim_time = simParameters["simulationTime"]
        r = rline.split(',')
        if fline:
            f = fline.split(',')
        else:
            f = r

        s.maxAvgLambda = simParameters["avgLambdaMax"]

        m_result = []
        m_traffic = []
        netSize = int(math.sqrt(len(r) / 10))
        numFlows = int(len(f) / (netSize * netSize * 10))
        globalPackets = 0
        globalLosses = 0
        globalDelay = 0
        offset = netSize * netSize * 3
        for src_node in range(netSize):
            new_result_row = []
            new_traffic_row = []
            for dst_node in range(netSize):
                offset_t = (src_node * netSize + dst_node) * 3
                offset_d = offset + (src_node * netSize + dst_node) * 7
                pcktsGen = float(r[offset_t + 1])
                pcktsDrop = float(r[offset_t + 2])
                pcktsDelay = float(r[offset_d])

                dict_result_srcdst = {}
                dict_result_agg = {
                    'PktsDrop': numpy.round(pcktsDrop / sim_time, 6),
                    "AvgDelay": pcktsDelay,
                    "p10": float(r[offset_d + 1]),
                    "p20": float(r[offset_d + 2]),
                    "p50": float(r[offset_d + 3]),
                    "p80": float(r[offset_d + 4]),
                    "p90": float(r[offset_d + 5]),
                    "Jitter": float(r[offset_d + 6])}

                if src_node != dst_node:
                    globalPackets += pcktsGen
                    globalLosses += pcktsDrop
                    globalDelay += pcktsDelay

                lst_result_flows = []
                lst_traffic_flows = []
                offset_f = netSize * netSize * numFlows * 3
                for flow in range(numFlows):
                    # Results:
                    dict_result_tmp = {}
                    offset_tf = (src_node * netSize * numFlows + dst_node * numFlows + flow) * 3
                    offset_df = offset_f + (src_node * netSize * numFlows + dst_node * numFlows + flow) * 7
                    dict_result_tmp = {
                        'PktsDrop': numpy.round(float(f[offset_tf + 2]) / sim_time, 6),
                        "AvgDelay": float(f[offset_df]),
                        "p10": float(f[offset_df + 1]),
                        "p20": float(f[offset_df + 2]),
                        "p50": float(f[offset_df + 3]),
                        "p80": float(f[offset_df + 4]),
                        "p90": float(f[offset_df + 5]),
                        "Jitter": float(f[offset_df + 6])}
                    lst_result_flows.append(dict_result_tmp)
                    # Traffic:
                    dict_traffic = {'AvgBw': float(f[offset_tf]) * 1000,
                                    'PktsGen': numpy.round(float(f[offset_tf + 1]) / sim_time, 6),
                                    'TotalPktsGen': float(f[offset_tf + 1]), 'ToS': 0}
                    self._timedistparams(dict_traffic)
                    self._sizedistparams(dict_traffic)
                    lst_traffic_flows.append(dict_traffic)

                dict_traffic_srcdst = {}
                # From kbps to bps
                dict_traffic_agg = {'AvgBw': float(r[offset_t]) * 1000,
                                    'PktsGen': numpy.round(pcktsGen / sim_time, 6),
                                    'TotalPktsGen': pcktsGen}

                dict_result_srcdst['AggInfo'] = dict_result_agg
                dict_result_srcdst['Flows'] = lst_result_flows
                dict_traffic_srcdst['AggInfo'] = dict_traffic_agg
                dict_traffic_srcdst['Flows'] = lst_traffic_flows
                new_result_row.append(dict_result_srcdst)
                new_traffic_row.append(dict_traffic_srcdst)

            m_result.append(new_result_row)
            m_traffic.append(new_traffic_row)
        m_result = numpy.asmatrix(m_result)
        m_traffic = numpy.asmatrix(m_traffic)
        s._set_performance_matrix(m_result)
        s._set_traffic_matrix(m_traffic)
        s._set_global_packets(numpy.round(globalPackets / sim_time, 6))
        s._set_global_losses(numpy.round(globalLosses / sim_time, 6))
        s._set_global_delay(globalDelay / (netSize * (netSize - 1)))

    # Dataset v0 only contain exponential traffic with avg packet size of 1000
    def _timedistparams(self, dict_traffic):
        """
    

        Parameters
        ----------
        dict_traffic: dictionary
            Dictionary to fill with the time distribution information
            extracted from data
    

        """

        dict_traffic['TimeDist'] = TimeDist.EXPONENTIAL_T
        params = {'EqLambda': dict_traffic['AvgBw'], 'AvgPktsLambda': dict_traffic['AvgBw'] / 1000, 'ExpMaxFactor': 10}
        dict_traffic['TimeDistParams'] = params

    # Dataset v0 only contains binomial traffic with avg packet size of 1000
    def _sizedistparams(self, dict_traffic):
        """
    

        Parameters
        ----------
        dict_traffic : dictionary
            Dictionary to fill with the size distribution information
            extracted from data

        """
        dict_traffic['SizeDist'] = SizeDist.BINOMIAL_S
        params = {'AvgPktSize': 1000, 'PktSize1': 300, 'PktSize2': 1700}
        dict_traffic['SizeDistParams'] = params





