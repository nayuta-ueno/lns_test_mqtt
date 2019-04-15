#!/bin/bash
set -eu

SUFFIX=
START_GENERATOR=0
TESTNAME=REQ2

KILLSH=kill_${TESTNAME}_${SUFFIX}.sh
LOGDIR=`pwd`/logs_${TESTNAME}_${SUFFIX}
ADDR=127.0.0.1

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

PORTBASE=`read_ini`
NODE1=$((PORTBASE))
NODE2=$((PORTBASE+10))
HOP=$((PORTBASE+20))

CLN=(${NODE1} ${NODE2})
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

NODEID1=`python3 clightning.py /tmp/light${NODE1}`
NODEID2=`python3 clightning.py /tmp/light${NODE2}`
HOPID=`python3 ptarm.py ${ADDR} ${HOP}`

echo TESTNAME= ${TESTNAME}
echo NODE1= ${NODEID1}
echo NODE2= ${NODEID2}
echo HOP=   ${HOPID}

nohup python3 mqtt_req2.py ${NODEID1} ${HOPID} ${NODEID2} > ${LOGDIR}/mqtt_req.log&
echo "kill -9 $!" >> ${KILLSH}
echo "rm ${KILLSH}" >> ${KILLSH}
