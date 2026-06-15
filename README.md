# Quartz

A hardware simulation and execution framework with Docker containerization and MongoDB backend.

## Prerequisites

Install the following using Homebrew:

```bash
brew install python@3.9
brew install docker
brew install verilator
brew install verible
brew install ghdl
brew install gcc
brew install make
```

## Setup

Run the setup command to initialize the project:

```bash
make setup
```

This will:
1. Create a Python virtual environment
2. Install Python dependencies
3. Build the MongoDB Docker image
4. Run the MongoDB container on port 27017

## Available Commands

- `make setup` - Initialize project with venv and spin up MongoDB
- `make build` - Build the Verilator sandbox Docker image

## Project Structure

- `agent/` - Agent modules
- `orchestrator/` - Orchestration logic
- `parser/` - Parsing utilities
- `router/` - Routing logic
- `rtl/` - RTL source files (Verilog, SystemVerilog, and VHDL)
- `runners/` - Execution runners for simulations
- `tests/` - Test files and testbenches
- `Dockerfile` - MongoDB container definition
- `sandbox/sandbox.Dockerfile` - Verilator sandbox container

## Running

With the venv activated:

```bash
source .venv/bin/activate
python runners/execution_runner.py
```

## Docker Containers

**MongoDB (quartz)**
- Port: 27017
- Started automatically with `make setup`

**Verilator Sandbox (quartz-sandbox)**
- Built with `make build`
- Contains Verilator, GHDL, build tools, and testbench environment
