# Image Settings
imageName=snap-hutao-generic-api
imageVersion=1.0

docker build --no-cache -f Dockerfile -t $imageName:$imageVersion --target runtime .