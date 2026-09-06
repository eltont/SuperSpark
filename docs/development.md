# Development

## Host prerequisites (this Mac)

- Portable tools under `~/.local/bin` (docker, kubectl, k3d, colima, limactl)
- Temurin JDK 17 at `~/.local/opt/jdk-17`
- Colima provides the Docker daemon (Docker Desktop not required)
- System Homebrew at `/opt/homebrew` is owned by another user and is not used

```bash
export PATH="$HOME/.local/bin:$PATH"
export JAVA_HOME="$HOME/.local/opt/jdk-17"
```

## Workflow

1. `make doctor`
2. `make bootstrap` (Colima + images + k3d + smoke)
3. `make scenarios SIZE=tiny`
4. `make report`

## Resource lock

Heavy jobs: `scripts/bootstrap/with_lock.sh <purpose> <cmd...>`
