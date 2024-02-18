#! /bin/bash

if [ $#  -lt 2  ]; then
	echo "Usage: $0 nameSpace microshift|openshift"
	exit 1
fi

TYPE="UNKNOW"
if [ $2 == "microshift" ]; then
  TYPE="NodePort"
elif [ $2 == "openshift" ]; then
  TYPE="LoadBalancer"
else
  echo "Second parameter must be either microshift or openshift."
  exit 3
fi


# set env variables
. ./setENV.sh
if [ -z "${RTSP_URL}" ]; then
    echo "Populate the setENV.sh script with the correct parameters and try again."
    exit 2
fi

# generate unique YAML file name and create it using your env variables
NAME="thermal-camera-`date +"%j-%H-%M-%S"`.yaml"
cat <<EOF > $NAME
# Save the output of this file and use kubectl create -f to import
# it into Kubernetes.
#
# Created with podman-4.7.2
apiVersion: v1
kind: Service
metadata:
  creationTimestamp: "2024-01-15T02:04:23Z"
  labels:
    app: thermal-camera-pod
  name: thermal-camera-pod
spec:
  ports:
  - name: "4000"
    nodePort: 32400
    port: 4000
    targetPort: 4000
  selector:
    app: thermal-camera-pod
  type: ${TYPE}
---
apiVersion: v1
kind: Pod
metadata:
  creationTimestamp: "2024-01-15T02:04:23Z"
  labels:
    app: thermal-camera-pod
  name: thermal-camera-pod
spec:
  containers:
  - env:
    - name: Y_OFFSET
      value: "${Y_OFFSET}"
    - name: X_OFFSET
      value: "${X_OFFSET}"
    - name: ALPHA
      value: "${ALPHA}"
    - name: RTSP_URL
      value: ${RTSP_URL}
    - name: T_LITE_URL
      value: ${T_LITE_URL}
    image: quay.io/andyyuen/thermalcamera:1.0
    name: thermal-camera
    ports:
    - containerPort: 4000
    securityContext:
      seccompProfile:
        type: RuntimeDefault
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      privileged: false
      readOnlyRootFilesystem: false
      runAsGroup: 1000
      runAsUser: 1000
      seLinuxOptions: {}
    workingDir: /app
EOF

echo "Created YAML file: $NAME"

# create name space if it does not exist
kubectl get ns $1 > /dev/null
if [ $? -eq 1 ]; then
    echo "Namespace does not exist: $1"
    echo "Creating ns: $1"
    kubectl create ns $1
fi
# deploy
kubectl create -f $NAME -n $1
