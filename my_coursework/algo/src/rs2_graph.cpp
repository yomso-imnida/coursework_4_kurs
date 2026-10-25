#include "SCHED/rs2_graph.hpp"

#include <fstream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>

namespace sched {
namespace {

std::size_t parse_number(const std::string& token, std::size_t line) {
    if (token.empty() || token.front() == '-') {
        throw std::runtime_error("ERROR: invalid number on line " +
                                 std::to_string(line));
    }

    std::size_t pos = 0;
    unsigned long long number;

    try {
        number = std::stoull(token, &pos);
    } catch (const std::exception&) {
        throw std::runtime_error("ERROR: invalid number on line " +
                                 std::to_string(line));
    }

    if (pos != token.size() ||
        number > std::numeric_limits<std::size_t>::max()) {
        throw std::runtime_error("ERROR: invalid number on line " +
                                 std::to_string(line));
    }

    return static_cast<std::size_t>(number);
}

struct RawNode {
    std::size_t weight;
    std::vector<std::size_t> children;
};

} // namespace

Rs2Graph Rs2Graph::read(const std::string& path) {
    std::ifstream input(path);

    if (!input) {
        throw std::runtime_error("ERROR: cannot open graph file: " + path);
    }

    std::string line;

    if (!std::getline(input, line)) {
        throw std::runtime_error("ERROR: empty graph file");
    }

    std::istringstream header(line);
    std::string node, size, children, extra;

    if (!(header >> node >> size >> children) ||
        node != "node" ||
        size != "size" ||
        children != "children" ||
        (header >> extra)) {
        throw std::runtime_error("ERROR: invalid RS2 graph header");
    }

    std::map<std::size_t, RawNode> nodes;
    std::size_t line_number = 1;

    while (std::getline(input, line)) {
        ++line_number;

        std::istringstream row(line);
        std::string id_token, weight_token, child_token;

        if (!(row >> id_token)) {
            continue;
        }

        if (!(row >> weight_token)) {
            throw std::runtime_error(
                "ERROR: missing weight on line " +
                std::to_string(line_number));
        }

        const auto id = parse_number(id_token, line_number);
        const auto weight = parse_number(weight_token, line_number);

        std::vector<std::size_t> child_ids;

        while (row >> child_token) {
            child_ids.push_back(parse_number(child_token, line_number));
        }

        if (!nodes.emplace(
                id, RawNode{weight, std::move(child_ids)}
            ).second) {
            throw std::runtime_error(
                "ERROR: duplicate node ID on line " +
                std::to_string(line_number));
        }
    }

    if (nodes.empty()) {
        throw std::runtime_error("ERROR: graph has no nodes");
    }

    Rs2Graph result;

    for (const auto& [id, info] : nodes) {
        result.original_ids.push_back(id);
        result.weights.push_back(info.weight);
    }

    for (const auto& [id, info] : nodes) {
        for (const auto child : info.children) {
            if (nodes.find(child) == nodes.end()) {
                throw std::runtime_error(
                    "ERROR: undefined child node " + std::to_string(child));
            }

            result.edges.emplace_back(id, child);
        }
    }

    return result;
}

} // namespace sched
