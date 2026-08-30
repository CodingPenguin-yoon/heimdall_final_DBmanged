# Heimdall Managed Database

Heimdall project application data를 소유하는 독립 PostgreSQL이다. Control PostgreSQL과 Docker
project runtime을 포함하지 않는다.

## Local

```bash
cp .env.example .env
# .env에 서로 다른 강한 admin/provisioner password를 설정한다.
docker compose --env-file .env up -d --wait
docker compose --env-file .env ps
```

`provisioner-bootstrap`은 PostgreSQL이 healthy가 된 뒤 매번 idempotent하게 실행되어 신규·기존
volume의 `heimdall_provisioner` role과 project deletion용 `pg_signal_backend` `SET` privilege를
보정하고 정상 종료한다. `docker compose ps -a`에서 이 one-shot service가 `Exited (0)`인 것은
정상이다. bootstrap이 실패하면 Control Plane Worker의 deletion preflight도 fail-fast하므로 원인을
해결하기 전에는 project database 삭제를 시도하지 않는다.

local PostgreSQL endpoint는 기본적으로 `127.0.0.1:55433`이다. Heimdall API와 project container는
Docker Desktop의 `host.docker.internal:55433`을 통해 연결한다. 이 Compose는
`heimdall-python-local` network에 참여하지 않는다.

data는 Git workspace가 아니라 `heimdall-managed-db-postgres` named volume에 저장된다.
`heimdall-python/.env`의 `HEIMDALL_MANAGED_DB_PROVISIONER_PASSWORD`에는 이 폴더의 `.env`와 같은
provisioner password를 설정한다. cluster admin password는 이 Managed DB 폴더에만 둔다.

## Managed DB VM

실제 VM에서는 전용 disk를 PostgreSQL data volume이 사용하는 Docker storage에 연결하고,
`HEIMDALL_MANAGED_DB_BIND_ADDRESS`를 VM private IP로 설정한다. `5432`는 Control/Runtime VM private
IP에만 허용하고 인터넷에는 공개하지 않는다.

Heimdall에는 다음 endpoint를 설정한다.

```text
HEIMDALL_MANAGED_DB_HOST=managed-db.internal
HEIMDALL_MANAGED_DB_PORT=5432
```

`docker compose down -v`는 database volume을 삭제하므로 의도적인 초기화 외에는 사용하지 않는다.
