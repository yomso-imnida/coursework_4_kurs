#pragma once

#include <boost/numeric/ublas/matrix.hpp>

#include <cstddef>
#include <string>

namespace sched {

class DelayMatrix {
public:
    boost::numeric::ublas::matrix<int> values;

    std::size_t processor_count() const noexcept {
        return values.size1();
    }

    static DelayMatrix read(const std::string& path);
};

} // namespace sched
