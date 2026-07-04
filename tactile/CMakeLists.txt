cmake_minimum_required(VERSION 3.16)
project(qctb_tactile_cic LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(TACTILE_USE_CUDA "Build with CUDA/TensorRT for Jetson Orin" OFF)

add_library(qctb_tactile STATIC
    TactileInferenceLoop.cpp
)
target_include_directories(qctb_tactile PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

if(TACTILE_USE_CUDA)
    find_package(CUDAToolkit REQUIRED)
    find_library(NVINFER nvinfer REQUIRED)
    target_compile_definitions(qctb_tactile PUBLIC TACTILE_USE_CUDA)
    target_link_libraries(qctb_tactile PUBLIC CUDA::cudart ${NVINFER})
endif()

add_executable(tactile_demo tactile_demo.cpp)
target_link_libraries(tactile_demo PRIVATE qctb_tactile)