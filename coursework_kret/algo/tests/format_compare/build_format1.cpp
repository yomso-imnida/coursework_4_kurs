#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

std::size_t read_unsigned(const std::string& token, const std::string& label) {
    if (token.empty() || token.find_first_not_of("0123456789") != std::string::npos) {
        throw std::runtime_error("invalid " + label + ": " + token);
    }
    std::size_t pos = 0;
    unsigned long long value = 0;
    try {
        value = std::stoull(token, &pos);
    } catch (const std::exception&) {
        throw std::runtime_error("invalid " + label + ": " + token);
    }
    if (pos != token.size() || value > std::numeric_limits<std::size_t>::max()) {
        throw std::runtime_error("invalid " + label + ": " + token);
    }
    return static_cast<std::size_t>(value);
}

std::size_t next_unsigned(std::istream& input, const std::string& label) {
    std::string token;
    if (!(input >> token)) {
        throw std::runtime_error("missing " + label);
    }
    return read_unsigned(token, label);
}

struct Graph {
    std::vector<std::size_t> weights;
    std::vector<std::pair<std::size_t, std::size_t>> edges;
};

Graph read_graph(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open intermediate graph: " + path.string());
    }

    const std::size_t n = next_unsigned(input, "number of tasks");
    const std::size_t m = next_unsigned(input, "number of edges");
    if (n == 0) {
        throw std::runtime_error("graph must contain at least one task");
    }

    Graph result;
    result.weights.reserve(n);
    for (std::size_t i = 0; i < n; ++i) {
        result.weights.push_back(next_unsigned(input, "task weight"));
    }

    result.edges.reserve(m);
    for (std::size_t i = 0; i < m; ++i) {
        const std::size_t from = next_unsigned(input, "edge source");
        const std::size_t to = next_unsigned(input, "edge target");
        if (from >= n || to >= n) {
            throw std::runtime_error("edge index is out of range");
        }
        result.edges.emplace_back(from, to);
    }

    std::string extra;
    if (input >> extra) {
        throw std::runtime_error("unexpected data after the last edge");
    }
    return result;
}

int read_delay(const std::string& token) {
    std::size_t pos = 0;
    long long value;
    try {
        value = std::stoll(token, &pos, 10);
    } catch (const std::exception&) {
        throw std::runtime_error("invalid delay matrix element: " + token);
    }
    if (pos != token.size() || value < std::numeric_limits<int>::min() ||
        value > std::numeric_limits<int>::max()) {
        throw std::runtime_error("invalid delay matrix element: " + token);
    }
    return static_cast<int>(value);
}

std::vector<std::vector<int>> read_matrix(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open delay matrix: " + path.string());
    }

    std::vector<std::vector<int>> matrix;
    std::string line;
    while (std::getline(input, line)) {
        std::istringstream row_stream(line);
        std::string token;
        std::vector<int> row;
        while (row_stream >> token) {
            row.push_back(read_delay(token));
        }
        if (!row.empty()) {
            matrix.push_back(std::move(row));
        }
    }

    const std::size_t p = matrix.size();
    if (p == 0) {
        throw std::runtime_error("delay matrix is empty");
    }
    for (const auto& row : matrix) {
        if (row.size() != p) {
            throw std::runtime_error("delay matrix is not square");
        }
    }
    return matrix;
}

void write_format1(const std::filesystem::path& path, const Graph& graph,
                   const std::vector<std::vector<int>>& matrix) {
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error("cannot create output: " + path.string());
    }

    const std::size_t n = graph.weights.size();
    const std::size_t p = matrix.size();
    const std::size_t m = graph.edges.size();
    if (n > static_cast<std::size_t>(std::numeric_limits<int>::max()) ||
        p > static_cast<std::size_t>(std::numeric_limits<int>::max()) ||
        m > static_cast<std::size_t>(std::numeric_limits<int>::max())) {
        throw std::runtime_error("N, P, or M exceeds the old parser's int limit");
    }

    output << n << ' ' << p << ' ' << m << '\n';

    for (std::size_t proc = 0; proc < p; ++proc) {
        for (std::size_t task = 0; task < n; ++task) {
            if (task != 0) output << ' ';
            output << graph.weights[task];
        }
        output << '\n';
    }

    for (const auto& row : matrix) {
        for (std::size_t col = 0; col < p; ++col) {
            if (col != 0) output << ' ';
            output << row[col];
        }
        output << '\n';
    }

    for (const auto& [from, to] : graph.edges) {
        output << from << ' ' << to << '\n';
    }
    output.close();
    if (!output) {
        throw std::runtime_error("error writing output: " + path.string());
    }
}

} // namespace

int main(int argc, char* argv[]) {
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0]
                  << " <intermediate.graph> <delays.txt> <output.in>\n";
        return 1;
    }

    try {
        const Graph graph = read_graph(argv[1]);
        const auto matrix = read_matrix(argv[2]);
        write_format1(argv[3], graph, matrix);
        std::cout << "OK: " << argv[3] << " (N=" << graph.weights.size()
                  << ", P=" << matrix.size() << ", M=" << graph.edges.size() << ")\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "ERROR: " << exc.what() << '\n';
        return 1;
    }
}
