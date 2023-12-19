# Docker Image Settings
imageName=snap-hutao-generic-api
containerName=Snap-Hutao-Generic-API
imageVersion=1.0
externalPort=3975
internalPort=8080

oldContainer=`docker ps -a| grep ${containerName} | head -1|awk '{print $1}' `
echo Delete old container...
docker rm  $oldContainer -f
echo Delete success
mkdir cache

docker build -f Dockerfile -t $imageName:$imageVersion .
docker run -d -itp $externalPort:$internalPort \
    -v $(pwd)/.env:/app/.env \
    -v $(pwd)/cache:/app/cache \
    --restart=always \
    --name="$containerName" \
    $imageName:$imageVersion