#!/bin/bash
set -eu

####################################################
read_ini() {
	# ini setting
	INI_FILE=config.ini
	INI_SECTION=${TESTNAME}

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

mqtt_client_start() {
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

echo ptarm: payer

SUFFIX=
START_GENERATOR=0
TESTNAME=REQ4_PAYER
ADDR=127.0.0.1

PORTBASE=`read_ini`
NODE1=$((PORTBASE))
NODE2=$((PORTBASE+10))
NODE3=$((PORTBASE+20))
NODE4=$((PORTBASE+30))
HOP=$((PORTBASE+40))

#          NODE1	NODE3		HOP 		NODE2 	    NODE4
NODE_SORT=(ptarm	clightning	clightning	clightning	clightning)
CLN=(${HOP} ${NODE2} ${NODE3} ${NODE4})
PTARM=(${NODE1})

####################

KILLSH=kill_${TESTNAME}_${SUFFIX}.sh
LOGDIR=`pwd`/logs_${TESTNAME}_${SUFFIX}
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
	nohup python3 mqtt_responser.py ${TESTNAME} clightning ${ADDR} ${i} /tmp/light${i} > ${LOGDIR}/mqtt_cln${i}.log&
	PID+=($!)
done
for i in ${PTARM[@]}; do
	nohup python3 mqtt_responser.py ${TESTNAME} ptarm ${ADDR} ${i} > ${LOGDIR}/mqtt_ptarm${i}.log&
	PID+=($!)
done

# c-lightning fund
for i in ${CLN[@]}; do
	./rrt_cln_pay.sh ${i}
done

# generator
if [ "${START_GENERATOR}" -eq 1 ]; then
	nohup ./regtestkeepfee.sh > /dev/null&
	PID+=($!)
fi

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

NODE1ID=`mqtt_client_start ${NODE_SORT[0]} ${NODE1}`
NODE3ID=`mqtt_client_start ${NODE_SORT[1]} ${NODE3}`
HOPID=`mqtt_client_start ${NODE_SORT[2]} ${HOP}`
NODE2ID=`mqtt_client_start ${NODE_SORT[3]} ${NODE2}`
NODE4ID=`mqtt_client_start ${NODE_SORT[4]} ${NODE4}`

echo TESTNAME= ${TESTNAME}
echo NODE1:${NODE_SORT[0]}:${NODE1}= ${NODE1ID}
echo NODE3:${NODE_SORT[1]}:${NODE3}= ${NODE3ID}
echo HOP:${NODE_SORT[2]}:${HOP}=   ${HOPID}
echo NODE2:${NODE_SORT[3]}:${NODE2}= ${NODE2ID}
echo NODE4:${NODE_SORT[4]}:${NODE4}= ${NODE4ID}

nohup python3 mqtt_req4.py ${TESTNAME} ${NODE1ID} ${NODE3ID} ${HOPID} ${NODE2ID} ${NODE4ID} > ${LOGDIR}/mqtt_req.log&
echo "kill -9 $!" >> ${KILLSH}
echo "rm ${KILLSH}" >> ${KILLSH}

echo started.
