#include "SCHED/delay_matrix.hpp"

#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace sched {

DelayMatrix DelayMatrix::read(const std::string& path) {
    std::ifstream input(path);

    if (!input) {
        throw std::runtime_error(
            "ERROR: cannot open delay matrix file: " + path);
    }

    std::vector<std::vector<int>> rows;
    std::string line;
    std::size_t columns = 0;

    while (std::getline(input, line)) {
        std::istringstream stream(line);
        std::vector<int> row;
        std::string token;

        while (stream >> token) {
            std::size_t pos = 0;
            long long value;

            try {
                value = std::stoll(token, &pos);
            } catch (const std::exception&) {
                throw std::runtime_error(
                    "ERROR: invalid delay matrix value");
            }

            if (pos != token.size() ||
                value < std::numeric_limits<int>::min() ||
                value > std::numeric_limits<int>::max()) {
                throw std::runtime_error(
                    "ERROR: invalid delay matrix value");
            }

            row.push_back(static_cast<int>(value));
        }

        if (row.empty()) {
            continue;
        }

        if (rows.empty()) {
            columns = row.size();
        } else if (row.size() != columns) {
            throw std::runtime_error(
                "ERROR: delay matrix is not square");
        }

        rows.push_back(std::move(row));
    }

    if (rows.empty() || rows.size() != columns) {
        throw std::runtime_error(
            "ERROR: delay matrix is not square");
    }

    DelayMatrix result;
    result.values.resize(rows.size(), columns, false);

    for (std::size_t i = 0; i < rows.size(); ++i) {
        for (std::size_t j = 0; j < columns; ++j) {
            result.values(i, j) = rows[i][j];
        }
    }

    return result;
}

} // namespace sched
