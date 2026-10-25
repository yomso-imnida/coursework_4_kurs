#include <unordered_map>
#include "SCHED/parser.hpp"
#include "SCHED/rs2_graph.hpp"
#include "SCHED/delay_matrix.hpp"
#include "SCHED/logger_config.hpp"
#include "SCHED/options.hpp"

#include <boost/numeric/ublas/io.hpp>
#include <boost/numeric/ublas/matrix.hpp>

#include <filesystem>
#include <fstream>

// Здечь считываем N P M и значения всех таблиц

namespace sched {

greedy::ScheduleData input_schedule_regular(std::string path,
                                        sched::input_class inp_class) {
    std::filesystem::path p(path);
    if (!std::filesystem::is_regular_file(p)) {
        throw std::runtime_error(
            "Not a regular file (opening a schedule file)");
    }
    LOG_DEBUG << "path: " << p;

    std::ifstream input(p);

    int task_num, proc_num, edge_num;
    input >> task_num >> proc_num >> edge_num;
    boost::numeric::ublas::matrix<std::size_t> task_time;
    if (inp_class == sched::input_class::class_2) {
        std::size_t time;
        input >> time;
        task_time =
            boost::numeric::ublas::scalar_matrix<std::size_t>(1, task_num) *
            time;
    } else {
        task_time =
            boost::numeric::ublas::matrix<std::size_t>(proc_num, task_num); // C

        // Считываем таблицу длительностей
        for (std::size_t i = 0; i < task_time.size1(); ++i) {
            for (std::size_t j = 0; j < task_time.size2(); ++j) {
                input >> task_time(i, j);
            }
        }
    }
    boost::numeric::ublas::matrix<int> tran_time(proc_num, proc_num); // D

    // Считываем таблицу времени передач
    for (std::size_t i = 0; i < tran_time.size1(); ++i) {
        for (std::size_t j = 0; j < tran_time.size2(); ++j) {
            input >> tran_time(i, j);
        }
    }
    std::vector<greedy::ScheduleData::Edge> edges;
    for (int i = 0; i < edge_num; ++i) {
        int a, b;
        input >> a >> b;
        edges.push_back({a, b});
    }
    return greedy::ScheduleData(edges, task_time, tran_time);
}

greedy::ScheduleData input_schedule_rs2(const std::string& graph_path,
                                        const std::string& matrix_path) {
    Rs2Graph graph = Rs2Graph::read(graph_path);
    DelayMatrix delays = DelayMatrix::read(matrix_path);

    const std::size_t proc_num = delays.processor_count();
    const std::size_t task_num = graph.weights.size();

    boost::numeric::ublas::matrix<std::size_t> task_time(proc_num, task_num);

    for (std::size_t i = 0; i < proc_num; ++i) {
        for (std::size_t j = 0; j < task_num; ++j) {
            task_time(i, j) = graph.weights[j];
        }
    }

    std::unordered_map<std::size_t, std::size_t> id_to_index;

    for (std::size_t i = 0; i < task_num; ++i) {
        id_to_index.emplace(graph.original_ids[i], i);
    }

    std::vector<greedy::ScheduleData::Edge> edges;
    edges.reserve(graph.edges.size());

    for (const auto& [from, to] : graph.edges) {
        edges.emplace_back(
            id_to_index.at(from),
            id_to_index.at(to)
        );
    }

    greedy::ScheduleData result(edges, task_time, delays.values);
    result.original_ids = graph.original_ids;

    return result;
}

} // namespace sched