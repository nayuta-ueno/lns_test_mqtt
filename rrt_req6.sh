#!/bin/bash
set -eu

####################################################
read_ini() {
	# ini setting
	INI_FILE=config.ini
	INI_SECTION=${TESTNAME}
	PORTBASE=0

	# ini parser
	eval `sed -e 's/[[:space:]]*\=[[:space:]]*/=/g' \
		-e 's/;.*$//' \
		-e 's/[[:space:]]*$//' \
		-e 's/^[[:space:]]*//' \
		-e "s/^\(.*\)=\([^\"']*\)$/\1=\"\2\"/" \
	< $INI_FILE \
		| sed -n -e "/^\[$INI_SECTION\]/,/^\s*\[/{/^[^;].*\=.*/p;}"`
	echo ${PORTBASE}
}

create_kill_script() {
	# create killall script
	touch ${KILLSH}
	echo "#!/bin/bash" > ${KILLSH}
	for i in ${PID[@]}; do
		echo "kill -9 ${i}" >> ${KILLSH}
	done
}

get_nodeid() {
	if [ "$1" == "clightning" ]; then
		python3 clightning.py /tmp/light$2
	elif [ "$1" == "ptarm" ]; then
		python3 ptarm.py ${ADDR} $2
	else
		echo Invalid argument: $1
		exit 1
	fi
}
####################################################

echo ptarm: hop

SUFFIX=
START_GENERATOR=0
TESTNAME=REQ6
ADDR=127.0.0.1

PORTBASE=`read_ini`
NODE_PORT=()		# all node port
NODE_TYPE=()		# node type
CLN_NUM=0

for i in `seq 0 9`; do
	port=$((PORTBASE+2*$i))
	NODE_PORT+=(${port})
	NODE_TYPE+=(clightning)
	CLN_NUM=$((CLN_NUM+1))
done

port=$((PORTBASE+20))
NODE_PORT+=(${port})
NODE_TYPE+=(ptarm)

####################

KILLSH=kill_${TESTNAME}_${SUFFIX}.sh
LOGDIR=`pwd`/logs_${TESTNAME}_${SUFFIX}
PIDS=()

rm -rf ${LOGDIR}
mkdir -p ${LOGDIR}
cp rrt_cln_daemon.sh ../lightning/

cd ..

echo !!! node start !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
cnt=0
for i in ${NODE_TYPE[@]}; do
	port=${NODE_PORT[${cnt}]}
	if [ $i == clightning ]; then
		cd ./lightning
		rm -rf rt${port}
		nohup ./lightningd/lightningd --network=regtest --lightning-dir=rt${port} --addr=${ADDR}:${port} --log-level=debug --rpc-file=/tmp/light${port} > ${LOGDIR}/cln${port}.log&
		PID+=($!)
		echo NODE clightning port=${port}:$!
		cd ..
	elif [ $i == ptarm ]; then
		cd ./ptarmigan/install
		rm -rf rt${port}
		./new_nodedir.sh rt${port}
		cd rt${port}
		nohup ../ptarmd --network=regtest --port ${port} > ${LOGDIR}/ptarm${port}.log&
		PID+=($!)
		echo NODE ptarm port=${port}:$!
		cd ../../..
	fi
	cnt=$((cnt+1))
done

cd lns_test_mqtt
create_kill_script

sleep 10

echo !!! client MQTT start !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
cnt=0
for i in ${NODE_TYPE[@]}; do
	port=${NODE_PORT[${cnt}]}
	if [ $i == clightning ]; then
		# responser
		nohup python3 mqtt_responser.py ${TESTNAME} clightning ${ADDR} ${port} /tmp/light${port} > ${LOGDIR}/mqtt_cln${port}.log&
		PID+=($!)
		echo MQTT clightning port=${port}:$!

		#fund
		./rrt_cln_pay.sh ${port}
	elif [ $i == ptarm ]; then
		# responser
		nohup python3 mqtt_responser.py ${TESTNAME} ptarm ${ADDR} ${port} > ${LOGDIR}/mqtt_ptarm${port}.log&
		PID+=($!)
		echo MQTT ptarm port=${port}:$!
	fi
	cnt=$((cnt+1))
	sleep 1
done

create_kill_script

# generator
if [ "${START_GENERATOR}" -eq 1 ]; then
	echo !!! generator start
	nohup ./regtestkeepfee.sh > /dev/null&
	PID+=($!)
fi

create_kill_script

# fund check
echo !!! fund check !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
while :
do
	cnt=0
	funded=0
	for i in ${NODE_TYPE[@]}; do
		port=${NODE_PORT[${cnt}]}
		if [ $i == clightning ]; then
			fund=`./rrt_cln_fund.sh ${port}`
			fund=`echo ${fund} | jq -e '. | length'`
			if [ ${fund} -ne 0 ]; then
				funded=$((funded+1))
			fi
		fi
		cnt=$((cnt+1))
	done
	if [ ${funded} -eq ${CLN_NUM} ]; then
		break
	fi
	echo funded=${funded}, clightning=${CLN_NUM}
	sleep 10
done

echo !!!!!!!!!!!!!!!!!!
echo !!! TEST START !!!
echo !!!!!!!!!!!!!!!!!!

NODEID=()
cnt=0
for i in ${NODE_TYPE[@]}; do
	port=${NODE_PORT[${cnt}]}
	NODEID+=(`get_nodeid $i ${port}`)
    echo PORT $i:${port}=${NODEID[${cnt}]}
	cnt=$((cnt+1))
done

echo python3 mqtt_req6.py ${TESTNAME} ${NODEID[@]}
nohup python3 mqtt_req6.py ${TESTNAME} ${NODEID[@]} > ${LOGDIR}/mqtt_req.log&
echo "kill -9 $!" >> ${KILLSH}
echo "rm ${KILLSH}" >> ${KILLSH}

echo started.
