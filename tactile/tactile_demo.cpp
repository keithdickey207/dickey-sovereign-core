#include "TactileInferenceLoop.hpp"
#include <cstdint>
#include <iostream>

int main() {
    qctb::QuantumOptimizer qopt;
    qctb::TactileInferenceLoop loop("models/tactile_net.engine");

    std::uint16_t cap[256]{};
    std::uint16_t piezo[32]{};
    for (int i = 0; i < 256; ++i) cap[i] = static_cast<std::uint16_t>(i * 10);
    for (int i = 0; i < 32; ++i) piezo[i] = static_cast<std::uint16_t>(1000 + i * 50);

    loop.set_quantum_optimizer(&qopt);
    for (std::uint64_t c = 0; c < 100; ++c) {
        auto out = loop.execute_step(cap, piezo, c);
        if (c % 10 == 0)
            std::cout << "cycle=" << c << " slip=" << out.slip_probability
                      << " delta=" << out.grip_force_delta << "\n";
    }
    return 0;
}