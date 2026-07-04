/**
 * QCTB Classical Inference Core — stub implementation for non-Jetson builds.
 * Link with TensorRT + CUDA on Orin: -DTACTILE_USE_CUDA
 */

#include "TactileInferenceLoop.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <iostream>

namespace qctb {

namespace {
constexpr std::size_t kCapSize = 16 * 16;
constexpr std::size_t kPiezoSize = 32;

float stub_slip(const std::uint16_t* cap, const std::uint16_t* piezo) {
    float cap_mean = 0.f;
    float piezo_var = 0.f;
    for (std::size_t i = 0; i < kCapSize; ++i) cap_mean += cap[i];
    cap_mean /= static_cast<float>(kCapSize);
    float piezo_mean = 0.f;
    for (std::size_t i = 0; i < kPiezoSize; ++i) piezo_mean += piezo[i];
    piezo_mean /= static_cast<float>(kPiezoSize);
    for (std::size_t i = 0; i < kPiezoSize; ++i) {
        float d = piezo[i] - piezo_mean;
        piezo_var += d * d;
    }
    piezo_var /= static_cast<float>(kPiezoSize);
    float slip = std::min(1.f, piezo_var / 65536.f + cap_mean / 65535.f * 0.1f);
    return slip;
}
}  // namespace

void QuantumOptimizer::submit_feature_vector(const float* features, std::size_t dim) {
    pending_.slip_threshold = 0.5f + 0.1f * (dim > 0 ? features[0] : 0.f);
    pending_.pid_kp_delta = 0.05f * (dim > 1 ? features[1] : 0.f);
    pending_.fusion_scale.clear();
    ready_ = true;
    if (callback_) callback_(pending_);
}

bool QuantumOptimizer::poll_result(QuantumInjection& out) {
    if (!ready_) return false;
    out = pending_;
    ready_ = false;
    return true;
}

TactileInferenceLoop::TactileInferenceLoop(const std::string& engine_path) {
#ifdef TACTILE_USE_CUDA
    cudaStreamCreate(&stream_);
    (void)engine_path;
    cuda_ready_ = false;
#else
    (void)engine_path;
    std::cerr << "[QCTB] Stub CIC — build with -DTACTILE_USE_CUDA on Jetson Orin\n";
#endif
}

TactileInferenceLoop::~TactileInferenceLoop() {
#ifdef TACTILE_USE_CUDA
    for (auto* p : h_buffers_) if (p) cudaFreeHost(p);
    if (stream_) cudaStreamDestroy(stream_);
    if (context_) context_->destroy();
    if (engine_) engine_->destroy();
    if (runtime_) runtime_->destroy();
#endif
}

TactileOutputs TactileInferenceLoop::execute_step(
    const std::uint16_t* capacitive_16x16,
    const std::uint16_t* piezo_window_32,
    std::uint64_t cycle_count) {

    TactileOutputs out{};
#ifdef TACTILE_USE_CUDA
    if (cuda_ready_ && context_) {
        std::memcpy(h_buffers_[0], capacitive_16x16, kCapSize * sizeof(std::uint16_t));
        std::memcpy(h_buffers_[1], piezo_window_32, kPiezoSize * sizeof(std::uint16_t));
        context_->enqueueV3(stream_);
        cudaStreamSynchronize(stream_);
        out.slip_probability = *static_cast<float*>(h_buffers_[2]);
        out.grip_force_delta = *static_cast<float*>(h_buffers_[3]);
    } else
#endif
    {
        out.slip_probability = stub_slip(capacitive_16x16, piezo_window_32);
        out.grip_force_delta = (0.5f - out.slip_probability) * 0.2f;
    }

    fusion_features_.assign(64, 0.f);
    for (std::size_t i = 0; i < 16 && i < fusion_features_.size(); ++i)
        fusion_features_[i] = capacitive_16x16[i] / 65535.f;

    if (q_optimizer_ && (cycle_count % kQuantumCycleInterval == 0))
        q_optimizer_->submit_feature_vector(fusion_features_.data(), fusion_features_.size());

    return out;
}

}  // namespace qctb