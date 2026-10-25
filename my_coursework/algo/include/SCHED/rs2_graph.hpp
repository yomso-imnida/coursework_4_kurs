#pragma once

#include <cstddef>
#include <string>
#include <utility>
#include <vector>

namespace sched {

class Rs2Graph {
public:
    using Edge = std::pair<std::size_t, std::size_t>;

    std::vector<std::size_t> weights;
    std::vector<Edge> edges;
    std::vector<std::size_t> original_ids;

    static Rs2Graph read(const std::string& path);
};

} // namespace sched
