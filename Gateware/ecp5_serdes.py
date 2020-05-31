from nmigen import *
from nmigen.build import *
from nmigen.lib.cdc import *

from serdes import *


__all__ = ["LatticeECP5PCIeSERDES"]


class LatticeECP5PCIeSERDES(Elaboratable): # From Yumewatari
    """
    Lattice ECP5 DCU configured in PCIe mode. Assumes 100 MHz reference clock on SERDES clock
    input pair. Uses 1:2 gearing. Receiver Detection runs in TX clock domain. Only provides
    a single lane.

    Parameters
    ----------
    ref_clk : Signal
        100 MHz SERDES reference clock.

    rx_clk_o : Signal
        125 MHz clock recovered from received data.
    rx_clk_i : Signal
        125 MHz clock for the receive FIFO.

    tx_clk_o : Signal
        125 MHz clock generated by transmit PLL.
    tx_clk_i : Signal
        125 MHz clock for the transmit FIFO.
    """

    def __init__(self, pins):
        self.ref_clk = Signal() # reference clock

        self.extref0.attr.add(("LOC", "EXTREF0"))

        self.rx_clk_o   = Signal()
        self.rx_clk_i   = Signal()
        self.rx_bus     = Signal(24)

        self.tx_clk_o   = Signal()
        self.tx_clk_i   = Signal()
        self.tx_bus     = Signal(24)
        self.__pins     = pins

    def elaborate(self, platform: Platform) -> Module:
        m = Module()
        pins = self.__pins

        extref0 = Instance("EXTREFB",
            i_REFCLKP=pins.clk_p,
            i_REFCLKN=pins.clk_n,
            o_REFCLKO=self.ref_clk,
            p_REFCK_PWDNB="0b1",
            p_REFCK_RTERM="0b1",            # 100 Ohm
        )
        extref0.attr.add(("LOC", "EXTREF0"))
        m.submodules += extref0

        # RX

        rxclk_d = ClockDomain(reset_less=True)
        m.domains.rx = rxclk_d
        m.d.comb += rxclk_d.clk.eq(self.rx_clk_i)

        rx_los   = Signal()
        rx_los_s = Signal()
        rx_lol   = Signal()
        rx_lol_s = Signal()
        rx_lsm   = Signal()
        rx_lsm_s = Signal()
        rx_inv   = Signal()
        rx_det   = Signal()

        m.submodules += [
            FFSynchronizer(rx_los, rx_los_s, o_domain="rx"),
            FFSynchronizer(rx_lol, rx_lol_s, o_domain="rx"),
            FFSynchronizer(rx_lsm, rx_lsm_s, o_domain="rx")
        ]

        # TX

        txclk_d = ClockDomain(reset_less=True)
        m.domains.tx = txclk_d
        m.d.comb += txclk_d.clk.eq(self.tx_clk_i)

        tx_lol   = Signal()
        tx_lol_s = Signal()

        m.submodules += [
            FFSynchronizer(tx_lol, tx_lol_s, o_domain="tx")
        ]

        self.lane = lane = PCIeSERDESInterface(ratio=2)

        m.d.comb += [
            rx_inv.eq(lane.rx_invert),
            rx_det.eq(lane.rx_align),
            lane.rx_present.eq(~rx_los_s),
            lane.rx_locked .eq(~rx_lol_s),
            lane.rx_aligned.eq(rx_lsm_s),
            lane.rx_symbol.eq(Cat(self.rx_bus[ 0: 9],
                                  self.rx_bus[12:21])),
            # In theory, ``rx_bus[9:11]`` has disparity error and coding violation status
            # signals, but in practice, they appear to be stuck at 1 and 0 respectively.
            # However, the 8b10b decoder replaces errors with a "K14.7", which is not a legal
            # point in 8b10b coding space, so we can use that as an indication.
            lane.rx_valid.eq(Cat(self.rx_bus[ 0: 9] != 0x1EE,
                                 self.rx_bus[12:21] != 0x1EE)),
        ]

        m.d.comb += [
            self.tx_bus.eq(Cat(lane.tx_symbol[0: 9],
                               lane.tx_set_disp[0], lane.tx_disp[0], lane.tx_e_idle[0],
                               lane.tx_symbol[9:18],
                               lane.tx_set_disp[1], lane.tx_disp[1], lane.tx_e_idle[1])),
        ]

        pcie_det_en = Signal()
        pcie_ct     = Signal()
        pcie_done   = Signal()
        pcie_done_s = Signal()
        pcie_con    = Signal()
        pcie_con_s  = Signal()

        det_timer = Signal(max=16)

        m.submodules += [
            FFSynchronizer(pcie_done, pcie_done_s, o_domain="tx"),
            FFSynchronizer(pcie_con, pcie_con_s, o_domain="tx")
        ]
        
        with m.FSM(domain="tx", reset=~lane.det_enable):
            with m.State("START"):
                # Before starting a Receiver Detection test, the transmitter must be put into
                # electrical idle by setting the tx_idle_ch#_c input high. The Receiver Detection
                # test can begin 120 ns after tx_elec_idle is set high by driving the appropriate
                # pci_det_en_ch#_c high.
                m.d.tx += det_timer.eq(15)
                next = "SET-DETECT-H"
            with m.State("SET-DETECT-H"):
                # 1. The user drives pcie_det_en high, putting the corresponding TX driver into
                #    receiver detect mode. [...] The TX driver takes some time to enter this state
                #    so the pcie_det_en must be driven high for at least 120ns before pcie_ct
                #    is asserted.
                with m.If(det_timer == 0):
                    m.d.tx += pcie_det_en.eq(1)
                    m.d.tx += det_timer.eq(15)
                    next = "SET-STROBE-H"
                with m.Else():
                    m.d.tx += det_timer.eq(det_timer - 1)
            with m.State("SET-STROBE-H"):
                # 2. The user drives pcie_ct high for four byte clocks.
                with m.If(det_timer == 0):
                    m.d.tx += pcie_ct.eq(1)
                    m.d.tx += det_timer.eq(3)
                    next = "SET-STROBE-L"
                with m.Else():
                    m.d.tx += det_timer.eq(det_timer - 1)
            with m.State("SET-STROBE-L"):
                # 3. SERDES drives the corresponding pcie_done low.
                # (this happens asynchronously, so we're going to observe a few samples of pcie_done
                # as high)
                with m.If(det_timer == 0):
                    m.d.tx += pcie_ct.eq(0)
                    next = "WAIT-DONE-L"
                with m.Else():
                    m.d.tx += det_timer.eq(det_timer - 1)
            with m.State("WAIT-DONE-L"):
                with m.If(~pcie_done_s):
                    next = "WAIT-DONE-H"
            with m.State("WAIT-DONE-H"):
                with m.If(pcie_done_s):
                    m.d.tx += lane.det_status.eq(pcie_con_s)
                    next = "DONE"
        
        dcu0 = Instance("DCUA", # Page 71 of TN1261
            #============================ DCU
            # DCU — power management
            p_D_MACROPDB            = "0b1",
            p_D_IB_PWDNB            = "0b1",    # undocumented (required for RX)
            p_D_TXPLL_PWDNB         = "0b1",
            i_D_FFC_MACROPDB        = 1,

            # DCU — reset
            i_D_FFC_MACRO_RST       = 0,
            i_D_FFC_DUAL_RST        = 0,
            i_D_FFC_TRST            = 0,

            # DCU — clocking
            i_D_REFCLKI             = self.ref_clk,
            o_D_FFS_PLOL            = tx_lol,
            p_D_REFCK_MODE          = "0b100",  # 25x REFCLK
            p_D_TX_MAX_RATE         = "2.5",    # 2.5 Gbps
            p_D_TX_VCO_CK_DIV       = "0b000",  # DIV/1
            p_D_BITCLK_LOCAL_EN     = "0b1",    # undocumented (PCIe sample code used)

            # DCU ­— unknown
            p_D_CMUSETBIASI         = "0b00",   # begin undocumented (PCIe sample code used)
            p_D_CMUSETI4CPP         = "0d4",
            p_D_CMUSETI4CPZ         = "0d3",
            p_D_CMUSETI4VCO         = "0b00",
            p_D_CMUSETICP4P         = "0b01",
            p_D_CMUSETICP4Z         = "0b101",
            p_D_CMUSETINITVCT       = "0b00",
            p_D_CMUSETISCL4VCO      = "0b000",
            p_D_CMUSETP1GM          = "0b000",
            p_D_CMUSETP2AGM         = "0b000",
            p_D_CMUSETZGM           = "0b100",
            p_D_SETIRPOLY_AUX       = "0b10",
            p_D_SETICONST_AUX       = "0b01",
            p_D_SETIRPOLY_CH        = "0b10",
            p_D_SETICONST_CH        = "0b10",
            p_D_SETPLLRC            = "0d1",
            p_D_RG_EN               = "0b1",
            p_D_RG_SET              = "0b00",   # end undocumented

            # DCU — FIFOs
            p_D_LOW_MARK            = "0d4",
            p_D_HIGH_MARK           = "0d12",

            #============================ CH0 common
            # CH0 — protocol
            p_CH0_PROTOCOL          = "PCIE",
            p_CH0_PCIE_MODE         = "0b1",

            #============================ CH0 receive
            # CH0 RX ­— power management
            p_CH0_RPWDNB            = "0b1",
            i_CH0_FFC_RXPWDNB       = 1,

            # CH0 RX ­— reset
            i_CH0_FFC_RRST          = 0,
            i_CH0_FFC_LANE_RX_RST   = 0,

            # CH0 RX ­— input
            i_CH0_HDINP             = pins.rx_p,
            i_CH0_HDINN             = pins.rx_n,
            i_CH0_FFC_SB_INV_RX     = rx_inv,

            p_CH0_RTERM_RX          = "0d22",   # 50 Ohm (wizard value used, does not match D/S, should be 0d19 there)
            p_CH0_RXIN_CM           = "0b11",   # CMFB (wizard value used)
            p_CH0_RXTERM_CM         = "0b11",   # RX Input (wizard value used)

            # CH0 RX ­— clocking
            i_CH0_RX_REFCLK         = self.ref_clk,
            o_CH0_FF_RX_PCLK        = self.rx_clk_o,
            i_CH0_FF_RXI_CLK        = self.rx_clk_i,

            p_CH0_CDR_MAX_RATE      = "2.5",    # 2.5 Gbps
            p_CH0_RX_DCO_CK_DIV     = "0b000",  # DIV/1
            p_CH0_RX_GEAR_MODE      = "0b1",    # 1:2 gearbox
            p_CH0_FF_RX_H_CLK_EN    = "0b1",    # enable  DIV/2 output clock
            p_CH0_FF_RX_F_CLK_DIS   = "0b1",    # disable DIV/1 output clock
            p_CH0_SEL_SD_RX_CLK     = "0b1",    # FIFO driven by recovered clock

            p_CH0_AUTO_FACQ_EN      = "0b1",    # undocumented (wizard value used)
            p_CH0_AUTO_CALIB_EN     = "0b1",    # undocumented (wizard value used)
            p_CH0_PDEN_SEL          = "0b1",    # phase detector disabled on LOS

            p_CH0_DCOATDCFG         = "0b00",   # begin undocumented (PCIe sample code used)
            p_CH0_DCOATDDLY         = "0b00",
            p_CH0_DCOBYPSATD        = "0b1",
            p_CH0_DCOCALDIV         = "0b010",
            p_CH0_DCOCTLGI          = "0b011",
            p_CH0_DCODISBDAVOID     = "0b1",
            p_CH0_DCOFLTDAC         = "0b00",
            p_CH0_DCOFTNRG          = "0b010",
            p_CH0_DCOIOSTUNE        = "0b010",
            p_CH0_DCOITUNE          = "0b00",
            p_CH0_DCOITUNE4LSB      = "0b010",
            p_CH0_DCOIUPDNX2        = "0b1",
            p_CH0_DCONUOFLSB        = "0b101",
            p_CH0_DCOSCALEI         = "0b01",
            p_CH0_DCOSTARTVAL       = "0b010",
            p_CH0_DCOSTEP           = "0b11",   # end undocumented

            # CH0 RX — loss of signal
            o_CH0_FFS_RLOS          = rx_los,
            p_CH0_RLOS_SEL          = "0b1",
            p_CH0_RX_LOS_EN         = "0b1",
            p_CH0_RX_LOS_LVL        = "0b100",  # Lattice "TBD" (wizard value used)
            p_CH0_RX_LOS_CEQ        = "0b11",   # Lattice "TBD" (wizard value used)

            # CH0 RX — loss of lock
            o_CH0_FFS_RLOL          = rx_lol,

            # CH0 RX — link state machine
            i_CH0_FFC_SIGNAL_DETECT = rx_det,
            o_CH0_FFS_LS_SYNC_STATUS= rx_lsm,
            p_CH0_ENABLE_CG_ALIGN   = "0b1",
            p_CH0_UDF_COMMA_MASK    = "0x3ff",  # compare all 10 bits
            p_CH0_UDF_COMMA_A       = "0x283",  # K28.5 inverted
            p_CH0_UDF_COMMA_B       = "0x17C",  # K28.5

            p_CH0_CTC_BYPASS        = "0b1",    # bypass CTC FIFO
            p_CH0_MIN_IPG_CNT       = "0b11",   # minimum interpacket gap of 4
            p_CH0_MATCH_4_ENABLE    = "0b1",    # 4 character skip matching
            p_CH0_CC_MATCH_1        = "0x1BC",  # K28.5
            p_CH0_CC_MATCH_2        = "0x11C",  # K28.0
            p_CH0_CC_MATCH_3        = "0x11C",  # K28.0
            p_CH0_CC_MATCH_4        = "0x11C",  # K28.0

            # CH0 RX — data
            **{"o_CH0_FF_RX_D_%d" % n: self.rx_bus[n] for n in range(self.rx_bus.width)},

            #============================ CH0 transmit
            # CH0 TX — power management
            p_CH0_TPWDNB            = "0b1",
            i_CH0_FFC_TXPWDNB       = 1,

            # CH0 TX ­— reset
            i_CH0_FFC_LANE_TX_RST   = 0,

            # CH0 TX ­— output
            o_CH0_HDOUTP            = pins.tx_p,
            o_CH0_HDOUTN            = pins.tx_n,

            p_CH0_TXAMPLITUDE       = "0d1000", # 1000 mV
            p_CH0_RTERM_TX          = "0d19",   # 50 Ohm

            p_CH0_TDRV_SLICE0_CUR   = "0b011",  # 400 uA
            p_CH0_TDRV_SLICE0_SEL   = "0b01",   # main data
            p_CH0_TDRV_SLICE1_CUR   = "0b000",  # 100 uA
            p_CH0_TDRV_SLICE1_SEL   = "0b00",   # power down
            p_CH0_TDRV_SLICE2_CUR   = "0b11",   # 3200 uA
            p_CH0_TDRV_SLICE2_SEL   = "0b01",   # main data
            p_CH0_TDRV_SLICE3_CUR   = "0b11",   # 3200 uA
            p_CH0_TDRV_SLICE3_SEL   = "0b01",   # main data
            p_CH0_TDRV_SLICE4_CUR   = "0b11",   # 3200 uA
            p_CH0_TDRV_SLICE4_SEL   = "0b01",   # main data
            p_CH0_TDRV_SLICE5_CUR   = "0b00",   # 800 uA
            p_CH0_TDRV_SLICE5_SEL   = "0b00",   # power down

            # CH0 TX ­— clocking
            o_CH0_FF_TX_PCLK        = self.tx_clk_o,
            i_CH0_FF_TXI_CLK        = self.tx_clk_i,

            p_CH0_TX_GEAR_MODE      = "0b1",    # 1:2 gearbox
            p_CH0_FF_TX_H_CLK_EN    = "0b1",    # enable  DIV/2 output clock
            p_CH0_FF_TX_F_CLK_DIS   = "0b1",    # disable DIV/1 output clock

            # CH0 TX — data
            **{"o_CH0_FF_TX_D_%d" % n: self.tx_bus[n] for n in range(self.tx_bus.width)},

            # CH0 DET
            i_CH0_FFC_PCIE_DET_EN   = pcie_det_en,
            i_CH0_FFC_PCIE_CT       = pcie_ct,
            o_CH0_FFS_PCIE_DONE     = pcie_done,
            o_CH0_FFS_PCIE_CON      = pcie_con,
        )
        dcu0.attr.add(("LOC", "DCU0"))
        dcu0.attr.add(("CHAN", "CH0"))
        dcu0.attr.add(("BEL", "X42/Y71/DCU"))
        m.submodules += dcu0
        return m