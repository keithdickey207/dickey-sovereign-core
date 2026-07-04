#pragma once
/**
 * QCTB Classical Inference Core (CIC) — Jetson Orin TensorRT runtime skeleton.
 * Zero-copy pinned memory + async quantum optimizer hook.
 * Copyright (c) 2026 Waterville Software Development Services
 */

#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#ifdef TACTILE_USE_CUDA
#include <cuda_runtime_api.h>
#include <NvInfer.h>
#endif

namespace qctb {

struct TactileOutputs {
    float slip_probability{0.f};
    float grip_force_delta{0.f};
};

struct QuantumInjection {
    float slip_threshold{0.5f};
    float pid_kp_delta{0.f};
    std::vector<float> fusion_scale;
};

using QuantumCallback = std::function<void(const QuantumInjection&)>;

class QuantumOptimizer {
public:
    void submit_feature_vector(const float* features, std::size_t dim);
    bool poll_result(QuantumInjection& out);
    void set_callback(QuantumCallback cb) { callback_ = std::move(cb); }
private:
    QuantumCallback callback_;
    QuantumInjection pending_{};
    bool ready_{false};
};

class TactileInferenceLoop {
public:
    explicit TactileInferenceLoop(const std::string& engine_path);
    ~TactileInferenceLoop();

    TactileInferenceLoop(const TactileInferenceLoop&) = delete;
    TactileInferenceLoop& operator=(const TactileInferenceLoop&) = delete;

    TactileOutputs execute_step(
        const std::uint16_t* capacitive_16x16,
        const std::uint16_t* piezo_window_32,
        std::uint64_t cycle_count);

    void set_quantum_optimizer(QuantumOptimizer* opt) { q_optimizer_ = opt; }
    static constexpr std::uint32_t kQuantumCycleInterval = 50;

private:
#ifdef TACTILE_USE_CUDA
    nvinfer1::IRuntime* runtime_{nullptr};
    nvinfer1::ICudaEngine* engine_{nullptr};
    nvinfer1::IExecutionContext* context_{nullptr};
    cudaStream_t stream_{};
    void* h_buffers_[4]{};
    void* d_buffers_[4]{};
    bool cuda_ready_{false};
#endif
    QuantumOptimizer* q_optimizer_{nullptr};
    std::vector<float> fusion_features_{};
};

}  // namespace qctb