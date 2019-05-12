#!/bin/bash

GENERATE_SEC=15

CHAIN=`bitcoin-cli getblockchaininfo | jq -r .chain`
echo ${CHAIN}
if [ ${CHAIN} != regtest ]; then
	echo REGTEST only
	exit 1
fi

payment() {
	LIST=`bitcoin-cli listunspent`
	num=0
	while :
	do
		AMOUNT=`echo ${LIST} | jq .[${num}].amount`
		AMOUNT=$(printf "%.8f" ${AMOUNT})
		echo "  AMOUNT=${AMOUNT}"
		# 10mBTC以上のamount
		SUB=`echo "${AMOUNT}*100/1" | bc`
		echo "     SUB=${SUB}"
		if [ ${SUB} -gt 0 ]; then
			echo "     break"
			break
		fi
		num=$((num+1))
	done
	TXID=`echo ${LIST} | jq .[${num}].txid`
	VOUT=`echo ${LIST} | jq .[${num}].vout`
	AMOUNT=`echo ${AMOUNT} - 0.000002 | bc`
	AMOUNT=$(printf "%.8f" ${AMOUNT})
	ADDR=`bitcoin-cli getnewaddress`

	TX=`bitcoin-cli createrawtransaction "[{\"txid\":${TXID},\"vout\":${VOUT}}]" "[{\"${ADDR}\":${AMOUNT}}]"`
	TX=`bitcoin-cli signrawtransactionwithwallet ${TX}`
	TX=`echo ${TX} | jq -r .hex`
	TXID=`bitcoin-cli sendrawtransaction ${TX}`
	echo PAY=${TXID}
}

cnt=0
while :
do
	FEERATE=`bitcoin-cli estimatesmartfee 6 | jq .feerate`
	if [ ${FEERATE} != null ]; then
		FEERATE=$(printf "%.8f" ${FEERATE})
		SUB=`echo "${FEERATE} - 0.00005000" | bc`
		#echo $SUB
		if [ ${SUB:0:1} == '-' ]; then
			echo FEERATE=${FEERATE}
			sleep ${GENERATE_SEC}
			bitcoin-cli sendtoaddress `bitcoin-cli getnewaddress` 0.0007
			bitcoin-cli generatetoaddress 1 `bitcoin-cli getnewaddress`
			cnt=0
			continue
		fi
	fi
	cnt=$((cnt+1))
	if [ ${cnt} -gt 10 ]; then
		echo -----------------
		bitcoin-cli generatetoaddress 1 `bitcoin-cli getnewaddress`
		cnt=0
	fi

	payment
done
