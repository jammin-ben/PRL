#!/bin/bash
sampled_traces="sampled_traces/"
for entry in "$sampled_traces"/*
do
	echo "$entry"
	str="python3 prl.py $entry > output"
	echo "$str"
	
done
