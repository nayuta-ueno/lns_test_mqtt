#!/bin/bash

CHAIN=`bitcoin-cli getblockchaininfo | jq -r .chain`
echo ${CHAIN}
if [ ${CHAIN} != regtest ]; then
	echo REGTEST only
	exit 1
fi

cnt=0
while :
do
	LIST=`bitcoin-cli listunspent`
	TXID=`echo ${LIST} | jq .[0].txid`
	VOUT=`echo ${LIST} | jq .[0].vout`
	AMOUNT=`echo ${LIST} | jq .[0].amount`
	AMOUNT=`echo ${AMOUNT} - 0.000002 | bc`
	AMOUNT=$(printf "%.8f" ${AMOUNT})
	ADDR=`bitcoin-cli getnewaddress`

	TX=`bitcoin-cli createrawtransaction "[{\"txid\":${TXID},\"vout\":${VOUT}}]" "[{\"${ADDR}\":${AMOUNT}}]"`
	TX=`bitcoin-cli signrawtransactionwithwallet ${TX}`
	TX=`echo ${TX} | jq -r .hex`
	TXID=`bitcoin-cli sendrawtransaction ${TX}`
	#echo ${TXID}
	FEERATE=`bitcoin-cli estimatesmartfee 6 | jq .feerate`
	#echo FEERATE=${FEERATE}
	if [ ${FEERATE} != null ]; then
		FEERATE=$(printf "%.8f" ${FEERATE})
		SUB=`echo "${FEERATE} - 0.00005000" | bc`
		#echo $SUB
		if [ ${SUB:0:1} == '-' ]; then
			break
		fi
	fi
	cnt=$((cnt+1))
	if [ ${cnt} -gt 10 ]; then
		bitcoin-cli generate 1
		cnt=0
	fi
done
bitcoin-cli estimatesmartfee 6
