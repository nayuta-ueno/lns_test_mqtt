#!/bin/bash

KILLSH=kill_req3.sh
LOGDIR=`pwd`/logs
ADDR=127.0.0.1
NODE1=1110
NODE2=1120
NODE3=1130
HOP=1140

CLN=(${NODE1} ${NODE2} ${NODE3})
PTARM=(${HOP})
PIDS=()

rm -rf ${LOGDIR}
mkdir -p ${LOGDIR}
cp rrt_cln_daemon.sh ../lightning/

# c-lightning
cd ../lightning
for i in ${CLN[@]}; do
	rm -rf rt${i}
	nohup ./lightningd/lightningd --network=regtest --lightning-dir=rt${i} --addr=${ADDR}:${i} --log-level=debug --rpc-file=/tmp/light${i} > ${LOGDIR}/cln${i}.log&
	PID+=($!)
done

# ptarmigan
cd ../ptarmigan/install
for i in ${PTARM[@]}; do
	rm -rf rt${i}
	./new_nodedir.sh rt${i}
	cd rt${i}
	nohup ../ptarmd --network=regtest --port ${i} > ${LOGDIR}/ptarm${i}.log&
	PID+=($!)
	cd ..
done
cd ../..

sleep 5

# responser
cd lns_test_mqtt
for i in ${CLN[@]}; do
	nohup python3 mqtt_responser.py clightning ${ADDR} ${i} /tmp/light${i} > ${LOGDIR}/cln_mqtt${i}.log&
	PID+=($!)
done
for i in ${PTARM[@]}; do
	nohup python3 mqtt_responser.py ptarm ${ADDR} ${i} > ${LOGDIR}/ptarm_mqtt${i}.log&
	PID+=($!)
done

# c-lightning fund
for i in ${CLN[@]}; do
	./rrt_cln_pay.sh ${i}
done

# generator
nohup ./regtestkeepfee.sh > /dev/null&
PID+=($!)

# create killall script
touch ${KILLSH}
echo "#!/bin/bash" > ${KILLSH}
for i in ${PID[@]}; do
	echo "kill -9 ${i}" >> ${KILLSH}
done

# fund check
while :
do
	cnt=0
	for i in ${CLN[@]}; do
		fund=`./rrt_cln_fund.sh ${i}`
		fund=`echo ${fund} | jq -e '. | length'`
		if [ ${fund} -ne 0 ]; then
			cnt=$((cnt+1))
		fi
	done
	if [ $cnt -eq ${#CLN[@]} ]; then
		break
	fi
	sleep 10
done

echo !!!!!!!!!!!!!!!!!!
echo !!! TEST START !!!
echo !!!!!!!!!!!!!!!!!!

NODEID1=`python3 clightning.py /tmp/light${NODE1}`
NODEID2=`python3 clightning.py /tmp/light${NODE2}`
NODEID3=`python3 clightning.py /tmp/light${NODE3}`
HOPID=`python3 ptarm.py ${ADDR} ${HOP}`

echo NODE1=${NODEID1}
echo NODE2=${NODEID2}
echo NODE3=${NODEID3}
echo HOP=${HOPID}

#nohup python3 mqtt_req3.py ${NODEID1} ${NODEID3} ${HOPID} ${NODEID2} > ${LOGDIR}/req3.log&
python3 mqtt_req3.py ${NODEID1} ${NODEID3} ${HOPID} ${NODEID2}
#echo "kill -9 $!" >> ${KILLSH}
