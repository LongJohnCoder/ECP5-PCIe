EESchema Schematic File Version 4
EELAYER 30 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 2 3
Title ""
Date ""
Rev ""
Comp ""
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L Si5325:Si5325 U?
U 4 1 5E815D50
P 3300 3250
AR Path="/5E815D50" Ref="U?"  Part="4" 
AR Path="/5E7EABA8/5E815D50" Ref="U1"  Part="4" 
F 0 "U1" H 3242 2685 50  0000 C CNN
F 1 "Si5325" H 3242 2776 50  0000 C CNN
F 2 "" H 2500 4100 50  0001 C CNN
F 3 "" H 2500 4100 50  0001 C CNN
	4    3300 3250
	1    0    0    1   
$EndComp
$Comp
L PCIe:ECP5_EVN_PCIe U?
U 3 1 5E815D5C
P 3750 3500
AR Path="/5E815D5C" Ref="U?"  Part="3" 
AR Path="/5E7EABA8/5E815D5C" Ref="U2"  Part="3" 
F 0 "U2" H 3750 3675 50  0000 C CNN
F 1 "ECP5_EVN_PCIe" H 3750 3584 50  0000 C CNN
F 2 "" H 3550 3550 50  0001 C CNN
F 3 "" H 3550 3550 50  0001 C CNN
	3    3750 3500
	-1   0    0    -1  
$EndComp
Wire Wire Line
	4250 3650 4500 3650
$Comp
L Device:C_Small C?
U 1 1 5EA9B70C
P 2900 3650
AR Path="/5EA9B70C" Ref="C?"  Part="1" 
AR Path="/5E7EABA8/5EA9B70C" Ref="C22"  Part="1" 
F 0 "C22" V 2671 3650 50  0000 C CNN
F 1 "100n" V 2762 3650 50  0000 C CNN
F 2 "Capacitor_SMD:C_0402_1005Metric" H 2900 3650 50  0001 C CNN
F 3 "~" H 2900 3650 50  0001 C CNN
	1    2900 3650
	0    1    1    0   
$EndComp
Wire Wire Line
	3000 3650 3250 3650
$Comp
L Device:C_Small C?
U 1 1 5EA9BBA0
P 3150 3550
AR Path="/5EA9BBA0" Ref="C?"  Part="1" 
AR Path="/5E7EABA8/5EA9BBA0" Ref="C23"  Part="1" 
F 0 "C23" V 2921 3550 50  0000 C CNN
F 1 "100n" V 3012 3550 50  0000 C CNN
F 2 "Capacitor_SMD:C_0402_1005Metric" H 3150 3550 50  0001 C CNN
F 3 "~" H 3150 3550 50  0001 C CNN
	1    3150 3550
	0    1    1    0   
$EndComp
Wire Wire Line
	3050 3550 2900 3550
$Comp
L Device:C_Small C?
U 1 1 5EA9C615
P 4350 3550
AR Path="/5EA9C615" Ref="C?"  Part="1" 
AR Path="/5E7EABA8/5EA9C615" Ref="C24"  Part="1" 
F 0 "C24" V 4121 3550 50  0000 C CNN
F 1 "100n" V 4212 3550 50  0000 C CNN
F 2 "Capacitor_SMD:C_0402_1005Metric" H 4350 3550 50  0001 C CNN
F 3 "~" H 4350 3550 50  0001 C CNN
	1    4350 3550
	0    1    1    0   
$EndComp
Wire Wire Line
	4450 3550 4600 3550
$Comp
L Device:C_Small C?
U 1 1 5EA9CB2F
P 4600 3650
AR Path="/5EA9CB2F" Ref="C?"  Part="1" 
AR Path="/5E7EABA8/5EA9CB2F" Ref="C25"  Part="1" 
F 0 "C25" V 4371 3650 50  0000 C CNN
F 1 "100n" V 4462 3650 50  0000 C CNN
F 2 "Capacitor_SMD:C_0402_1005Metric" H 4600 3650 50  0001 C CNN
F 3 "~" H 4600 3650 50  0001 C CNN
	1    4600 3650
	0    1    1    0   
$EndComp
Text Label 4250 3550 1    50   ~ 0
CLKINECP+
Text Label 4250 3650 3    50   ~ 0
CLKINECP-
Text Label 3250 3550 1    50   ~ 0
CLKOUTECP+
Text Label 3250 3650 3    50   ~ 0
CLKOUTECP-
Wire Wire Line
	4600 3100 4500 3100
Wire Wire Line
	4700 3200 4700 3650
Text Label 4700 3200 0    50   ~ 0
CLKOUT2-
Wire Wire Line
	4600 3100 4600 3550
Wire Wire Line
	4700 3200 4500 3200
Text Label 4600 3100 0    50   ~ 0
CLKOUT2+
$Comp
L Si5325:Si5325 U?
U 5 1 5E815D56
P 4200 3250
AR Path="/5E815D56" Ref="U?"  Part="5" 
AR Path="/5E7EABA8/5E815D56" Ref="U1"  Part="5" 
F 0 "U1" H 4142 2685 50  0000 C CNN
F 1 "Si5325" H 4142 2776 50  0000 C CNN
F 2 "" H 3400 4100 50  0001 C CNN
F 3 "" H 3400 4100 50  0001 C CNN
	5    4200 3250
	-1   0    0    1   
$EndComp
Text Label 2800 3200 2    50   ~ 0
CLKIN2-
Wire Wire Line
	2800 3200 2800 3650
Text Label 2900 3100 2    50   ~ 0
CLKIN2+
Wire Wire Line
	2900 3100 2900 3550
Wire Wire Line
	2900 3100 3000 3100
Wire Wire Line
	3000 3200 2800 3200
Text HLabel 3000 2900 0    50   Input ~ 0
CLKINp
Text HLabel 3000 3000 0    50   Input ~ 0
CLKINn
Text HLabel 4500 3000 2    50   Output ~ 0
CLKOUTn
Text HLabel 4500 2900 2    50   Output ~ 0
CLKOUTp
$EndSCHEMATC
