#include <boost/describe/enum_from_string.hpp>
#include <boost/describe/enum_to_string.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/program_options.hpp>
#include <boost/timer/timer.hpp>

#include "SCHED/greedy/greedy_algo.hpp"
#include "SCHED/parser.hpp"
#include "SCHED/json_dumper.hpp"
#include "SCHED/logger_config.hpp"
#include "SCHED/options.hpp"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <cstdlib>
#include <ctime>
#include <stdexcept>
#include <string>
#include <unistd.h>

// Для seed-а
unsigned long mix(unsigned long a, unsigned long b, unsigned long c) {
    a = a - b;
    a = a - c;
    a = a ^ (c >> 13);
    b = b - c;
    b = b - a;
    b = b ^ (a << 8);
    c = c - a;
    c = c - b;
    c = c ^ (b >> 13);
    a = a - b;
    a = a - c;
    a = a ^ (c >> 12);
    b = b - c;
    b = b - a;
    b = b ^ (a << 16);
    c = c - a;
    c = c - b;
    c = c ^ (b >> 5);
    a = a - b;
    a = a - c;
    a = a ^ (c >> 3);
    b = b - c;
    b = b - a;
    b = b ^ (a << 10);
    c = c - a;
    c = c - b;
    c = c ^ (b >> 15);
    return c;
}

int main(int argc, char* argv[]) {
    try {
        unsigned long seed = mix(clock(), time(NULL), getpid());
        srand(seed);

        namespace po = boost::program_options;

        po::options_description global("General descriptions");

        global.add_options()
            ("log,l",
             po::value<boost::log::trivial::severity_level>()
                 ->default_value(boost::log::trivial::debug),
             "Log level: 0-trace, 1-debug, 2-info, 3-warning, 4-error, 5-fatal")

            ("input,i", po::value<std::string>(),
             "Input file (format 1)")

            ("graph", po::value<std::string>(),
             "RS2 graph file (format 2)")

            ("matrix", po::value<std::string>(),
             "Delay matrix file (format 2)")

            ("output,o", po::value<std::string>()->required(),
             "Output file")

            ("conf", po::value<std::string>()->required(),
             "Config file path")

            ("command", po::value<std::string>()->required(),
             "Algorithm to execute")

            ("random", po::value<int>()->required(),
             "Fix METIS random flag");

        po::positional_options_description pos;
        pos.add("command", 1);

        po::variables_map vm;

        po::store(
            po::command_line_parser(argc, argv)
                .options(global)
                .positional(pos)
                .run(),
            vm
        );

        po::notify(vm);

        const bool has_input = vm.count("input") != 0;
        const bool has_graph = vm.count("graph") != 0;
        const bool has_matrix = vm.count("matrix") != 0;

        if ((has_input && (has_graph || has_matrix)) ||
            (!has_input && !(has_graph && has_matrix))) {
            throw std::runtime_error(
                "specify either --input or both --graph and --matrix"
            );
        }

        sched::init(
            vm["log"].as<boost::log::trivial::severity_level>()
        );

        std::string algo = vm["command"].as<std::string>();

        if (algo != "misf" &&
            algo != "edfbase" &&
            algo != "edffollow" &&
            algo != "edfb_misf" &&
            algo != "edff_misf" &&
            algo != "est" &&
            algo != "eft") {
            throw std::runtime_error("not a known algo");
        }

        sched::base_config conf =
            sched::parse_base_config(vm["conf"].as<std::string>());

        LOG_INFO << "Starting";

        boost::timer::cpu_timer timer;

        sched::greedy::ScheduleData schedule = has_input
            ? sched::input_schedule_regular(
                  vm["input"].as<std::string>(),
                  conf._class
              )
            : sched::input_schedule_rs2(
                  vm["graph"].as<std::string>(),
                  vm["matrix"].as<std::string>()
              );

        sched::greedy::TimeDiagram time_schedule =
            sched::greedy::heuristics(
                schedule,
                conf,
                algo,
                vm["random"].as<int>()
            );

        auto algo_time = timer.elapsed();

        LOG_INFO << "dumping to "
                 << vm["output"].as<std::string>();

        sched::Output_data out_data =
            time_schedule.extract_data(conf);

        if (has_graph) {
            for (auto& proc : out_data.proc_array) {
                for (auto& task : proc) {
                    task.task_no = schedule.original_ids.at(task.task_no);
                }
            }
        }

        sched::dump_to_json(
            vm["output"].as<std::string>(),
            out_data,
            (algo_time.system + algo_time.user) / (uint64_t)1e6
        );

        return 0;

    } catch (const std::exception& ex) {
        std::string message = ex.what();

        std::cerr
            << (message.rfind("ERROR:", 0) == 0 ? "" : "ERROR: ")
            << message << '\n';

        return 1;
    }
}
