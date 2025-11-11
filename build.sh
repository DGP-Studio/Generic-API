git pull --recurse-submodules && git submodule update --init --recursive
python3 cake.py
docker compose pull --ignore-buildable
docker compose up --build -d
