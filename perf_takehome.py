"""
# Anthropic's Original Performance Engineering Take-home (Release version)

Copyright Anthropic PBC 2026. Permission is granted to modify and use, but not
to publish or redistribute your solutions so it's hard to find spoilers.

# Task

- Optimize the kernel (in KernelBuilder.build_kernel) as much as possible in the
  available time, as measured by test_kernel_cycles on a frozen separate copy
  of the simulator.

Validate your results using `python tests/submission_tests.py` without modifying
anything in the tests/ folder.

We recommend you look through problem.py next.
"""

from collections import defaultdict
import random
import unittest

from problem import (
    Engine,
    DebugInfo,
    SLOT_LIMITS,
    VLEN,
    N_CORES,
    SCRATCH_SIZE,
    Machine,
    Tree,
    Input,
    HASH_STAGES,
    reference_kernel,
    build_mem_image,
    reference_kernel2,
)


class KernelBuilder:
    def __init__(self):
        self.instrs = []
        self.scratch = {}
        self.scratch_debug = {}
        self.scratch_ptr = 0
        self.const_map = {}

    def debug_info(self):
        return DebugInfo(scratch_map=self.scratch_debug)

    def build(self, slots: list[dict[Engine, list[tuple]]], vliw: bool = False):
        """
        When vliw=False (default): Original behavior
        When vliw=True: Future enhancement for automatic packing
        """
        if not vliw:
            # Original behavior with support for manual dict-based multi-slot instructions
            instrs = []
            for instr in slots:
                for engine, slotList in instr.items():
                    for slot in slotList:
                        instrs.append({engine: [slot]})
            return instrs
        
        instrs = []
        for instr in slots:
            instrs.append( instr )
        return instrs

    def add(self, engine, slot):
        self.instrs.append({engine: [slot]})

    def alloc_scratch(self, name=None, length=1):
        addr = self.scratch_ptr
        if name is not None:
            self.scratch[name] = addr
            self.scratch_debug[addr] = (name, length)
        self.scratch_ptr += length
        assert self.scratch_ptr <= SCRATCH_SIZE, "Out of scratch space"
        return addr

    def scratch_const(self, val, name=None):
        if val not in self.const_map:
            addr = self.alloc_scratch(name)
            self.add("load", ("const", addr, val))
            self.const_map[val] = addr
        return self.const_map[val]

    def scratch_two_const(self,val1,val2):
        addr1 = self.alloc_scratch()
        addr2 = self.alloc_scratch()
        self.const_map[val1] = addr1
        self.const_map[val2] = addr2
        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        instr["load"].append(("const",addr1,val1))
        instr["load"].append(("const",addr2,val2))
        return instr

    def build_hash(self, val_hash_addr, tmp1, tmp2, round, i):
        slots = []

        for hi, (op1, val1, op2, op3, val3) in enumerate(HASH_STAGES):
            slots.append(("alu", (op1, tmp1, val_hash_addr, self.scratch_const(val1))))
            slots.append(("alu", (op3, tmp2, val_hash_addr, self.scratch_const(val3))))
            slots.append(("alu", (op2, val_hash_addr, tmp1, tmp2)))
            #slots.append(("debug", ("compare", val_hash_addr, (round, i, "hash_stage", hi))))

        return slots

    def build_kernel(
        self, forest_height: int, n_nodes: int, batch_size: int, rounds: int
    ):
        """
        Like reference_kernel2 but building actual instructions.
        Scalar implementation using only scalar ALU and load/store.
        """
        batch_load_size = 4
        tmp1 = self.alloc_scratch("tmp1",batch_load_size*VLEN)
        tmp2 = self.alloc_scratch("tmp2",batch_load_size*VLEN)
        tmp3 = self.alloc_scratch("tmp3",VLEN)
        tmp4 = self.alloc_scratch("tmp4",VLEN)
        tmp5 = self.alloc_scratch("tmp5",VLEN)
        tmp6 = self.alloc_scratch("tmp6",VLEN)
        tmp7 = self.alloc_scratch("tmp7",VLEN)
        tmp8 = self.alloc_scratch("tmp8",VLEN)
        tmp9 = self.alloc_scratch("tmp9",VLEN)
        tmp1_vec = []
        tmp2_vec = []
        for i in range(batch_load_size):
            tmp1_vec.append(tmp1+i*VLEN)
            tmp2_vec.append(tmp2+i*VLEN)
        # Scratch space addresses
        init_vars = [
            "rounds",
            "n_nodes",
            "batch_size",
            "forest_height",
            "forest_values_p",
            "inp_indices_p",
            "inp_values_p",
            "extra_room",
        ]
        for v in init_vars:
            self.alloc_scratch(v, 1)
        node_val_addr = []
        inp_val_addr = self.scratch["inp_values_p"]
        forest_val_addr = self.scratch["forest_values_p"]

        body = []  # array of slots
        # hash const and multiplier
        for i in range(VLEN,batch_load_size*VLEN, VLEN*2):
            instr = self.scratch_two_const(i,i+VLEN)
            body.append(instr)
        instr = self.scratch_two_const(4,0)
        body.append(instr)
        zero_const = self.scratch_const(0)
        four_const = self.scratch_const(4)
        zero_const_vec = self.alloc_scratch("zero_const_vec",VLEN)
        two_const_vec = self.alloc_scratch("two_const_vec",VLEN)
        four_const_vec = self.alloc_scratch("four_const_vec",VLEN)
        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        instr["load"].append(("vload",self.scratch["rounds"],zero_const))
        #addr = self.alloc_scratch()
        #self.const_map[4] = addr
        #instr["load"].append(("const",addr,4))
        body.append(instr)
        instr = self.scratch_two_const(1,2)
        body.append(instr)
        one_const = self.scratch_const(1)
        two_const = self.scratch_const(2)
        instr = self.scratch_two_const(4097,19)
        body.append(instr)
        instr["valu"].append(("vbroadcast", two_const_vec, two_const ))
        instr["valu"].append(("vbroadcast", four_const_vec, four_const ))
        instr = self.scratch_two_const(33,9)
        body.append(instr)
        hash_val3_const = []
        hash_val3_const.append(self.scratch_const(4097))
        hash_val3_const.append(self.scratch_const(19))
        hash_val3_const.append(self.scratch_const(33))
        hash_val3_const.append(self.scratch_const(9))
        hash_val3_const.append(self.scratch_const(9))
        hash_val3_const.append(self.scratch_const(16))
        instr = self.scratch_two_const(0x7ED55D16,0xC761C23C)
        body.append(instr)
        instr = self.scratch_two_const(0x165667B1,0xD3A2646C)
        body.append(instr)
        instr = self.scratch_two_const(0xFD7046C5,0xB55A4F09)
        body.append(instr)
        hash_val1_const = []
        hash_val1_const.append(self.scratch_const(0x7ED55D16))
        hash_val1_const.append(self.scratch_const(0xC761C23C))
        hash_val1_const.append(self.scratch_const(0x165667B1))
        hash_val1_const.append(self.scratch_const(0xD3A2646C))
        hash_val1_const.append(self.scratch_const(0xFD7046C5))
        hash_val1_const.append(self.scratch_const(0xB55A4F09))

        # Pause instructions are matched up with yield statements in the reference
        # kernel to let you debug at intermediate steps. The testing harness in this
        # file requires these match up to the reference kernel's yields, but the
        # submission harness ignores them.
        self.add("flow", ("pause",))
        # Any debug engine instruction is ignored by the submission simulator
        self.add("debug", ("comment", "Starting loop"))

        # Scalar scratch registers
        tmp_idx = self.alloc_scratch("tmp_idx",batch_load_size*VLEN)
        tmp_val = self.alloc_scratch("tmp_val",batch_load_size*VLEN)
        node_val = self.alloc_scratch("node_val",batch_load_size*VLEN)
        # let index be 1-2047
        tmp_idx_vec = []
        tmp_val_vec = []
        node_val_vec = []
        next_node_val_1_vec = []
        next_node_val_2_vec = []
        next_node_val_1 = self.alloc_scratch("next_node_val1",batch_load_size*VLEN)
        next_node_val_2 = self.alloc_scratch("next_node_val2",batch_load_size*VLEN)
        store_load_val_addr = self.alloc_scratch("store_load_val_addr",batch_load_size)
        next_store_load_val_addr = self.alloc_scratch("next_store_load_val_addr",batch_load_size)
        store_load_val_addr_vec = []
        next_store_load_val_addr_vec = []
        next_addr = self.alloc_scratch("next_addr", 2 * batch_load_size*VLEN)
        load_addr_vec = []
        for i in range(batch_load_size) :
            tmp_idx_vec.append(tmp_idx+i * VLEN)
            tmp_val_vec.append(tmp_val+i * VLEN)
            node_val_vec.append(node_val+i * VLEN)
            next_node_val_1_vec.append( next_node_val_1+i * VLEN)
            next_node_val_2_vec.append( next_node_val_2+i * VLEN)
            store_load_val_addr_vec.append(store_load_val_addr+i)
            next_store_load_val_addr_vec.append(next_store_load_val_addr+i)
        for j in range(2):
            next_addr_vec = []
            for i in range(batch_load_size) :
                next_addr_vec.append(next_addr + i * VLEN + j * batch_load_size * VLEN )
            load_addr_vec.append(next_addr_vec)
        next_node_val = []
        next_node_val.append( next_node_val_1_vec )
        next_node_val.append( next_node_val_2_vec )

        # vec const value
        node_val_addr.append(self.scratch["forest_values_p"])
        hash_val3_const_vec = []
        hash_val1_const_vec = []
        # val3 of op4 and op5 are same( both 9)
        for i in range(6):
             hash_val3_const_vec.append(self.alloc_scratch(f"hash_val3_const_{i}_vec",VLEN))
             hash_val1_const_vec.append(self.alloc_scratch(f"hash_val1_const_{i}_vec",VLEN))

        preload_level = 4
        preload_size = 1 << (preload_level+1)
        tmp_preload_size = (1 << preload_level) - 2
        merge_vec_idx = [0,2,6]
        for i in range(1,preload_size//VLEN):
            node_val_addr.append(self.alloc_scratch(f"node_val_addr_VLEN_{i}"))
        valMod2 = self.alloc_scratch("valMod2",preload_level*batch_load_size*VLEN)
        valMod2_vec_level = []
        for j in range(preload_level):
            valMod2_vec = []
            for i in range(batch_load_size):
                valMod2_vec.append(valMod2+ i*VLEN + j*batch_load_size*VLEN)
            valMod2_vec_level.append(valMod2_vec)
        const_node_val_vec = self.alloc_scratch("const_node_val_vec",preload_size)
        node_val_preload_vec = []
        for i in range(preload_size):
            node_val_preload_vec.append(self.alloc_scratch(f"node_val_preload_vec_{i}",VLEN))

        merge_node_vec = []
        tmp_node_val_merge = self.alloc_scratch("tmp_node_val_merge",tmp_preload_size*batch_load_size*VLEN)
        for i in range(tmp_preload_size):
            tmp_addr = []
            for j in range(batch_load_size):
                tmp_addr.append(tmp_node_val_merge+j*VLEN+i*batch_load_size*VLEN)
            merge_node_vec.append(tmp_addr)
        node_val_addr_minus_one_vec = self.alloc_scratch("node_val_addr_minus_one_vec",VLEN)

        # rewrite to append slots into instructions with different lines
        # no need to broadcast 0
        #instr.update({"valu":[("vbroadcast",zero_const_vec,zero_const)]})
        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        instr["valu"].append(("vbroadcast", hash_val3_const_vec[0], hash_val3_const[0] ))
        instr["valu"].append(("vbroadcast", hash_val3_const_vec[1], hash_val3_const[1] ))
        instr["valu"].append(("vbroadcast", hash_val3_const_vec[2], hash_val3_const[2] ))
        instr["valu"].append(("vbroadcast", hash_val3_const_vec[3], hash_val3_const[3] ))
        instr["valu"].append(("vbroadcast", hash_val3_const_vec[5], hash_val3_const[5] ))
        instr["valu"].append(("vbroadcast", hash_val1_const_vec[0], hash_val1_const[0]))
        instr["alu"].append(("+", store_load_val_addr_vec[0], inp_val_addr, zero_const))
        instr["alu"].append(("+", store_load_val_addr_vec[1], inp_val_addr, self.scratch_const(VLEN)))
        instr["alu"].append(("+", store_load_val_addr_vec[2], inp_val_addr, self.scratch_const(2*VLEN)))
        instr["alu"].append(("+", store_load_val_addr_vec[3], inp_val_addr, self.scratch_const(3*VLEN)))
        instr["alu"].append(("+",node_val_addr[1],node_val_addr[0],self.scratch_const(VLEN)))
        instr["alu"].append(("+",node_val_addr[2],node_val_addr[0],self.scratch_const(2*VLEN)))
        instr["alu"].append(("+",node_val_addr[3],node_val_addr[0],self.scratch_const(3*VLEN)))
        # preload node_val[0:7] into const_node_val_vec
        instr["load"].append(("vload",const_node_val_vec,node_val_addr[0]))
        body.append(instr)

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        for os in range(0,6):
            instr["valu"].append(("vbroadcast", node_val_preload_vec[os], const_node_val_vec+os ))
        for os in range(0,8):
            instr["alu"].append(("+",node_val_preload_vec[6]+os,const_node_val_vec+6,zero_const))
        for os in range(0,4):
            instr["alu"].append(("+",node_val_preload_vec[7]+os,const_node_val_vec+7,zero_const))
        # preload tmp_val = values[0:7]
        instr["load"].append(("vload",tmp_val_vec[0],store_load_val_addr_vec[0]))
        # preload tmp_val = values[16:23]
        instr["load"].append(("vload",tmp_val_vec[2],store_load_val_addr_vec[2]))
        body.append(instr)
        hash_val3_const_vec[4] = hash_val3_const_vec[3]

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        for os in range(1,5):
            instr["valu"].append(("vbroadcast", hash_val1_const_vec[os], hash_val1_const[os]))
        for os in range(0,8):
            instr["alu"].append(("+", hash_val1_const_vec[5]+os, hash_val1_const[5], zero_const ))
        for os in range(4,8):
            instr["alu"].append(("+",node_val_preload_vec[7]+os,const_node_val_vec+7,zero_const))
        # pre calculate tmp_val = tmp_val ^ node_val[0]
        instr["valu"].append(("^",tmp_val_vec[0],tmp_val_vec[0],node_val_preload_vec[0]))
        instr["valu"].append(("^",tmp_val_vec[2],tmp_val_vec[2],node_val_preload_vec[0]))
        instr["load"].append(("vload",const_node_val_vec+VLEN,node_val_addr[1]))
        instr["load"].append(("vload",const_node_val_vec+2*VLEN,node_val_addr[2]))
        body.append(instr)

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        for os in range(8,14):
            instr["valu"].append(("vbroadcast", node_val_preload_vec[os], const_node_val_vec+os))
        instr["load"].append(("vload",const_node_val_vec+3*VLEN,node_val_addr[3]))
        # preload tmp_val = values[8:15]
        instr["load"].append(("vload",tmp_val_vec[1],store_load_val_addr_vec[1]))
        body.append(instr)

        batch_stride = self.scratch_const(batch_load_size*VLEN)

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        for os in range(14,20):
            instr["valu"].append(("vbroadcast", node_val_preload_vec[os], const_node_val_vec+os ))
        for os in range(0,4):
            instr["alu"].append(("+", next_store_load_val_addr_vec[os],store_load_val_addr_vec[os],batch_stride ))
        for os in range(0,8):
            instr["alu"].append(("-", node_val_addr_minus_one_vec+os, forest_val_addr, one_const ))
        # preload tmp_val = values[24:31]
        instr["load"].append(("vload",tmp_val_vec[3],store_load_val_addr_vec[3]))
        body.append(instr)

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        for os in range(20,26):
            instr["valu"].append(("vbroadcast", node_val_preload_vec[os], const_node_val_vec+os ))
        for os in range(0,8):
            instr["alu"].append(("-",node_val_preload_vec[2]+os,node_val_preload_vec[2],node_val_preload_vec[1]))
        body.append(instr)

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        for os in range(26,32):
            instr["valu"].append(("vbroadcast", node_val_preload_vec[os], const_node_val_vec+os ))
        body.append(instr)

        print("n_nodes=", n_nodes)
        print("SCRATCH_SIZE=", SCRATCH_SIZE)

        # notice initial index of all elements in batch are 0. It means each round index will be in the same level of the tree
        # for round #1, broadcast const zero to all index
        # for round #2, select between const one and const two based on val%2
        # 256 / 8 / 4 = 8
        for i in range(0,batch_size, batch_load_size * VLEN):
            # idx = 0
            # val = mem[inp_values_p + i]
            # node_val = node_val[0]
            # 16
            # unroll
            for round in range(rounds):
                level = round%(forest_height+1)
                # handle different levels
                # node_val can be loaded from 3 levels above and then use vselect/select
                # each level would need 8 * 4 / 2 = 16 instructions to load node_val
                # level 0-3(index 0:14) are preloaded. 16 * 5 = 10 * 8. so level 4-8 can have only 10 instructions while level 9 have to have 16 instructions
                if level == forest_height:
                    # next level is 0 so idx will all be 0, we can preload node_val = node_val[0] for all elements and preset idx = 0
                    # val = myhash(val ^ node_val) - vectorized for all 8 elements 
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp_val_vec[0], node_val_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp_val_vec[2], node_val_vec[2]))
                    body.append(instr)
                    # hash #
                    # 1: val = (val + 0x7ED55D16) + (val << 12) = 4097 * val + 0x7ED55D16
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[0], tmp_val_vec[0], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[0], tmp_val_vec[2], hash_val1_const_vec[0]))
                    # next level is 0 and idx is 0, node_val is node_val[0]
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp_val_vec[1], node_val_vec[1]))
                    instr["valu"].append(("^", tmp_val_vec[3], tmp_val_vec[3], node_val_vec[3]))
                    body.append(instr)
                    # 2: val = ( val ^ 0xC761C23C ) ^ (val >> 19)
                    # shift 1,3 vec to next instr
                    # tmp1 = val ^ 0xC761C23C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[1]))
                    # tmp2 = val >> 19
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[1]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add",tmp_val_vec[1],hash_val3_const_vec[0],tmp_val_vec[1],hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add",tmp_val_vec[3],hash_val3_const_vec[0],tmp_val_vec[3],hash_val1_const_vec[0]))
                    # next level is 0 and idx is 0, node_val is node_val[0]
                    body.append(instr)
                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[1]))
                    body.append(instr)
                    # 3: val = ( val + 0x165667B1 ) + ( val << 5 ) = 33 * val + 0x165667B1
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[2], tmp_val_vec[0], hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[2], tmp_val_vec[2], hash_val1_const_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^",tmp_val_vec[1],tmp1_vec[1],tmp2_vec[1]))
                    instr["valu"].append(("^",tmp_val_vec[3],tmp1_vec[3],tmp2_vec[3]))
                    # next level is 0 and idx is 0, node_val is node_val[0]
                    body.append(instr)
                    # 4: val = ( val + 0xD3A2646C ) ^ ( val << 9 )
                    # tmp1 = val + 0xD3A2646C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("+", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[3]))
                    # tmp2 = val << 9
                    instr["valu"].append(("<<", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[3]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1],hash_val3_const_vec[2],tmp_val_vec[1],hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3],hash_val3_const_vec[2],tmp_val_vec[3],hash_val1_const_vec[2]))
                    body.append(instr)
                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("+", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[3]))
                    body.append(instr)
                    # 5: val = ( val + 0xFD7046C5 ) + ( val << 3 ) = 9 * val + 0xFD7046C5
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[4], tmp_val_vec[0], hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[4], tmp_val_vec[2], hash_val1_const_vec[4]))
                    # pre calculate 0xB55A4F09 ^ node_val[0]
                    instr["valu"].append(("^",tmp1_vec[0], hash_val1_const_vec[5], node_val_preload_vec[0]))
                    instr["valu"].append(("^",tmp1_vec[2], hash_val1_const_vec[5], node_val_preload_vec[0]))
                    for os in range(0,8):
                        instr["alu"].append(("^",tmp1_vec[1]+os, hash_val1_const_vec[5], node_val_preload_vec[0]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^",tmp_val_vec[1],tmp1_vec[1],tmp2_vec[1]))
                    instr["valu"].append(("^",tmp_val_vec[3],tmp1_vec[3],tmp2_vec[3]))
                    body.append(instr)
                    # 6].appen)val = ( val ^ 0xB55A4F09 ) ^ ( val >> 16 )
                    # tmp1 = val ^ 0xB55A4F09 ^ node_val[0]
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], tmp1_vec[0]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], tmp1_vec[2]))
                    # tmp2 = val >> 16
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[5]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add",tmp_val_vec[1],hash_val3_const_vec[4],tmp_val_vec[1],hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add",tmp_val_vec[3],hash_val3_const_vec[4],tmp_val_vec[3],hash_val1_const_vec[4]))
                    for os in range(0,8):
                        instr["alu"].append(("^",tmp1_vec[3]+os, hash_val1_const_vec[5], node_val_preload_vec[0]))
                    body.append(instr)
                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], tmp1_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], tmp1_vec[3]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[5]))
                    body.append(instr)
                # special handling for preloaded levels, node_val for node_val[2**level-1:2**(level+1)-1) are pre-loaded
                elif level == 0:
                    addr_idx = 0
                    # val = myhash(val ^ node_val) - vectorized for all 8 elements 
                    # hash #
                    # 1: val = (val + 0x7ED55D16) + (val << 12) = 4097 * val + 0x7ED55D16
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[0], tmp_val_vec[0], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[0], tmp_val_vec[2], hash_val1_const_vec[0]))
                    if round == (forest_height+1):
                        # instr 1,3 shifted
                        instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                        instr["valu"].append(("^", tmp_val_vec[3], tmp1_vec[3], tmp2_vec[3]))
                    else:
                        # pre calculate tmp_val = tmp_val ^ node_val[0]
                        instr["valu"].append(("^", tmp_val_vec[1], tmp_val_vec[1], node_val_preload_vec[0]))
                        instr["valu"].append(("^", tmp_val_vec[3], tmp_val_vec[3], node_val_preload_vec[0]))
                    instr["valu"].append(("vbroadcast", tmp_idx_vec[0], one_const ))
                    instr["valu"].append(("vbroadcast", tmp_idx_vec[2], one_const ))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    # 2: val = ( val ^ 0xC761C23C ) ^ (val >> 19)
                    # tmp1 = val ^ 0xC761C23C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[1]))
                    # tmp2 = val >> 19
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[1]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[1], hash_val3_const_vec[0], tmp_val_vec[1], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3], hash_val3_const_vec[0], tmp_val_vec[3], hash_val1_const_vec[0]))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[1]))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    # 3: val = ( val + 0x165667B1 ) + ( val << 5 ) = 33 * val + 0x165667B1
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[2], tmp_val_vec[0], hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[2], tmp_val_vec[2], hash_val1_const_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    instr["valu"].append(("^", tmp_val_vec[3], tmp1_vec[3], tmp2_vec[3]))
                    instr["valu"].append(("vbroadcast", tmp_idx_vec[1], one_const ))
                    instr["valu"].append(("vbroadcast", tmp_idx_vec[3], one_const ))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    # 4: val = ( val + 0xD3A2646C ) ^ ( val << 9 )
                    # tmp1 = val + 0xD3A2646C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("+", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[3]))
                    # tmp2 = val << 9
                    instr["valu"].append(("<<", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[3]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1],hash_val3_const_vec[2],tmp_val_vec[1],hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3],hash_val3_const_vec[2],tmp_val_vec[3],hash_val1_const_vec[2]))
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("+", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[3]))
                    body.append(instr)

                    # 5: val = ( val + 0xFD7046C5 ) + ( val << 3 ) = 9 * val + 0xFD7046C5
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[4], tmp_val_vec[0], hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[4], tmp_val_vec[2], hash_val1_const_vec[4]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    instr["valu"].append(("^", tmp_val_vec[3], tmp1_vec[3], tmp2_vec[3]))
                    body.append(instr)

                    # 6: val = ( val ^ 0xB55A4F09 ) ^ ( val >> 16 )
                    # tmp1 = val ^ 0xB55A4F09
                    ### not implemented
                    # val%2 before 6th operation is val%2 before 3rd operation
                    # so final val%2 = (tmp2%2) == (val(before 3rd)%2)
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[5]))
                    # tmp2 = val >> 16
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[5]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1], hash_val3_const_vec[4], tmp_val_vec[1], hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3], hash_val3_const_vec[4], tmp_val_vec[3], hash_val1_const_vec[4]))
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[5]))
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("%", valMod2_vec_level[0][0], tmp_val_vec[0], two_const_vec))
                    instr["valu"].append(("%", valMod2_vec_level[0][2], tmp_val_vec[2], two_const_vec))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    instr["valu"].append(("^", tmp_val_vec[3], tmp1_vec[3], tmp2_vec[3]))
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("%", valMod2_vec_level[0][1], tmp_val_vec[1], two_const_vec))
                    for os in range(0,8):
                        instr["alu"].append(("%", valMod2_vec_level[0][3]+os, tmp_val_vec[3]+os, two_const_vec))
                    # node_val = (node_val[2]-node_val[1]) * val%2 + node_val[1]
                    instr["valu"].append(("multiply_add", node_val_vec[0], valMod2_vec_level[0][0], node_val_preload_vec[2], node_val_preload_vec[1]))
                    instr["valu"].append(("multiply_add", node_val_vec[2], valMod2_vec_level[0][2], node_val_preload_vec[2], node_val_preload_vec[1]))
                    # preprocess node_val picking for level 1
                    instr["flow"].append(("vselect", merge_node_vec[0][0], valMod2_vec_level[0][0], node_val_preload_vec[5], node_val_preload_vec[3]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # node_val = next_node_val1 + (val%2) * (next_node_val2 - next_node_val1)

                # special handling for preloaded levels, node_val for node_val[2**level-1:2**(level+1)-1) are pre-loaded
                elif level == 1:
                    # val = myhash(val ^ node_val) - vectorized for all 8 elements 
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp_val_vec[0], node_val_vec[0]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[2]+os, tmp_val_vec[2]+os, node_val_vec[2]+os))
                    # level1 idx = 2 * idx + 1 = 2 * (valMod2_level[0]+1) + 1 = 2 * valMod2_level[0] + 3
                    instr["valu"].append(("multiply_add", tmp_idx_vec[0], tmp_idx_vec[0], two_const_vec, valMod2_vec_level[0][0]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[2], tmp_idx_vec[2], two_const_vec, valMod2_vec_level[0][2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", node_val_vec[1], valMod2_vec_level[0][1], node_val_preload_vec[2], node_val_preload_vec[1]))
                    instr["valu"].append(("multiply_add", node_val_vec[3], valMod2_vec_level[0][3], node_val_preload_vec[2], node_val_preload_vec[1]))
                    # preprocess node_val picking for level 1
                    instr["flow"].append(("vselect", merge_node_vec[1][0], valMod2_vec_level[0][0], node_val_preload_vec[6], node_val_preload_vec[4]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # hash #
                    # 1: val = (val + 0x7ED55D16) + (val << 12) = 4097 * val + 0x7ED55D16
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[0], tmp_val_vec[0], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[0], tmp_val_vec[2], hash_val1_const_vec[0]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp_val_vec[1], node_val_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp_val_vec[3]+os, node_val_vec[3]+os))
                    # level1 idx = 2 * idx + 1 = 2 * (valMod2_level[0]+1) + 1 = 2 * valMod2_level[0] + 3
                    instr["valu"].append(("multiply_add", tmp_idx_vec[1], tmp_idx_vec[1], two_const_vec, valMod2_vec_level[0][1]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[3], tmp_idx_vec[3], two_const_vec, valMod2_vec_level[0][3]))
                    # preprocess node_val picking for level 1
                    instr["valu"].append(("-", merge_node_vec[1][0], merge_node_vec[1][0], merge_node_vec[0][0]))
                    instr["flow"].append(("vselect", merge_node_vec[0][1], valMod2_vec_level[0][1], node_val_preload_vec[5], node_val_preload_vec[3]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # 2: val = ( val ^ 0xC761C23C ) ^ (val >> 19)
                    # tmp1 = val ^ 0xC761C23C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[1]))
                    # tmp2 = val >> 19
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[2]+os, tmp_val_vec[2]+os, hash_val3_const_vec[1]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1], hash_val3_const_vec[0], tmp_val_vec[1], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3], hash_val3_const_vec[0], tmp_val_vec[3], hash_val1_const_vec[0]))
                    # preprocess node_val picking for level 1
                    instr["flow"].append(("vselect", merge_node_vec[1][1], valMod2_vec_level[0][1], node_val_preload_vec[6], node_val_preload_vec[4]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[3]+os, tmp_val_vec[3]+os, hash_val3_const_vec[1]))
                    # preprocess node_val picking for level 1
                    instr["valu"].append(("-", merge_node_vec[1][1], merge_node_vec[1][1], merge_node_vec[0][1]))
                    instr["flow"].append(("vselect", merge_node_vec[0][2], valMod2_vec_level[0][2], node_val_preload_vec[5], node_val_preload_vec[3]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # 3: val = ( val + 0x165667B1 ) + ( val << 5 ) = 33 * val + 0x165667B1
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[2], tmp_val_vec[0], hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[2], tmp_val_vec[2], hash_val1_const_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp1_vec[3]+os, tmp2_vec[3]+os))
                    # preprocess node_val picking for level 1
                    instr["flow"].append(("vselect", merge_node_vec[1][2], valMod2_vec_level[0][2], node_val_preload_vec[6], node_val_preload_vec[4]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # 4: val = ( val + 0xD3A2646C ) ^ ( val << 9 )
                    # tmp1 = val + 0xD3A2646C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("+", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[3]))
                    # tmp2 = val << 9
                    instr["valu"].append(("<<", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[3]))
                    for os in range(0,8):
                        instr["alu"].append(("<<", tmp2_vec[2]+os, tmp_val_vec[2]+os, hash_val3_const_vec[3]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1], hash_val3_const_vec[2], tmp_val_vec[1], hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3], hash_val3_const_vec[2], tmp_val_vec[3], hash_val1_const_vec[2]))
                    # preprocess node_val picking for level 1
                    instr["valu"].append(("-", merge_node_vec[1][2], merge_node_vec[1][2], merge_node_vec[0][2]))
                    instr["flow"].append(("vselect", merge_node_vec[0][3], valMod2_vec_level[0][3], node_val_preload_vec[5], node_val_preload_vec[3]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("+", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[3]))
                    for os in range(0,8):
                        instr["alu"].append(("<<", tmp2_vec[3]+os, tmp_val_vec[3]+os, hash_val3_const_vec[3]))
                    # preprocess node_val picking for level 1
                    instr["flow"].append(("vselect", merge_node_vec[1][3], valMod2_vec_level[0][3], node_val_preload_vec[6], node_val_preload_vec[4]))
                    # preprocess node_val picking for level 2
                    body.append(instr)

                    # 5: val = ( val + 0xFD7046C5 ) + ( val << 3 ) = 9 * val + 0xFD7046C5
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[4], tmp_val_vec[0], hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[4], tmp_val_vec[2], hash_val1_const_vec[4]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp1_vec[3]+os, tmp2_vec[3]+os))
                    # preprocess node_val picking for level 1
                    instr["valu"].append(("-", merge_node_vec[1][3], merge_node_vec[1][3], merge_node_vec[0][3]))
                    # preprocess node_val picking for level 2
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+0][0], valMod2_vec_level[0][0], node_val_preload_vec[11], node_val_preload_vec[7]))
                    body.append(instr)

                    # 6: val = ( val ^ 0xB55A4F09 ) ^ ( val >> 16 )
                    # tmp1 = val ^ 0xB55A4F09
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[5]))
                    # tmp2 = val >> 16
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[5]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[2]+os, tmp_val_vec[2]+os, hash_val3_const_vec[5]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add",tmp_val_vec[1],hash_val3_const_vec[4],tmp_val_vec[1],hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add",tmp_val_vec[3],hash_val3_const_vec[4],tmp_val_vec[3],hash_val1_const_vec[4]))
                    # preprocess node_val picking for level 2
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+2][0], valMod2_vec_level[0][0], node_val_preload_vec[13], node_val_preload_vec[9]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[5]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[3]+os, tmp_val_vec[3]+os, hash_val3_const_vec[5]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+2][0], merge_node_vec[merge_vec_idx[1]+2][0], merge_node_vec[merge_vec_idx[1]+0][0]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+1][0], valMod2_vec_level[0][0], node_val_preload_vec[12], node_val_preload_vec[8]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("%", valMod2_vec_level[1][0], tmp_val_vec[0], two_const_vec))
                    instr["valu"].append(("%", valMod2_vec_level[1][2], tmp_val_vec[2], two_const_vec))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp1_vec[3]+os, tmp2_vec[3]+os))
                    # preprocess node_val picking for level 2
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+3][0], valMod2_vec_level[0][0], node_val_preload_vec[14], node_val_preload_vec[10]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    # instr 1,3 shifted
                    instr["valu"].append(("%", valMod2_vec_level[1][1], tmp_val_vec[1], two_const_vec))
                    for os in range(0,8):
                        instr["alu"].append(("%", valMod2_vec_level[1][3]+os, tmp_val_vec[3]+os, two_const_vec))
                    # idx = (2 * idx + 1) + val%2
                    instr["valu"].append(("multiply_add", tmp_idx_vec[0], tmp_idx_vec[0], two_const_vec, valMod2_vec_level[1][0]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[2], tmp_idx_vec[2], two_const_vec, valMod2_vec_level[1][2]))
                    # preprocess node_val picking for level 1
                    # node_val = (node_val[2]-node_val[1]) * val%2 + node_val[1]
                    instr["valu"].append(("multiply_add", node_val_vec[0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[0]+1][0], merge_node_vec[merge_vec_idx[0]+0][0]))
                    instr["valu"].append(("multiply_add", node_val_vec[2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[0]+1][2], merge_node_vec[merge_vec_idx[0]+0][2]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+3][0], merge_node_vec[merge_vec_idx[1]+3][0], merge_node_vec[merge_vec_idx[1]+1][0]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+0][2], valMod2_vec_level[0][2], node_val_preload_vec[11], node_val_preload_vec[7]))
                    body.append(instr)

                    # node_val = next_node_val1 + (val%2) * (next_node_val2 - next_node_val1)
                # special handling for preloaded levels, node_val for node_val[2**level-1:2**(level+1)-1) are pre-loaded
                elif level == 2:
                    # val = myhash(val ^ node_val) - vectorized for all 8 elements 
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp_val_vec[0], node_val_vec[0]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[2]+os, tmp_val_vec[2]+os, node_val_vec[2]+os))
                    # preprocess node_val picking for level 1
                    instr["valu"].append(("multiply_add", node_val_vec[1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[0]+1][1], merge_node_vec[merge_vec_idx[0]+0][1]))
                    instr["valu"].append(("multiply_add", node_val_vec[3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[0]+1][3], merge_node_vec[merge_vec_idx[0]+0][3]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[1]+2][0], merge_node_vec[merge_vec_idx[1]+0][0]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+1][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[1]+3][0], merge_node_vec[merge_vec_idx[1]+1][0]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+2][2], valMod2_vec_level[0][2], node_val_preload_vec[13], node_val_preload_vec[9]))
                    body.append(instr)

                    # hash #
                    # 1: val = (val + 0x7ED55D16) + (val << 12) = 4097 * val + 0x7ED55D16
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[0], tmp_val_vec[0], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[0], tmp_val_vec[2], hash_val1_const_vec[0]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp_val_vec[1], node_val_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp_val_vec[3]+os, node_val_vec[3]+os))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+2][2], merge_node_vec[merge_vec_idx[1]+2][2], merge_node_vec[merge_vec_idx[1]+0][2]))
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+1][0], merge_node_vec[merge_vec_idx[1]+1][0], merge_node_vec[merge_vec_idx[1]+0][0]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+1][2], valMod2_vec_level[0][2], node_val_preload_vec[12], node_val_preload_vec[8]))
                    body.append(instr)

                    # 2: val = ( val ^ 0xC761C23C ) ^ (val >> 19)
                    # tmp1 = val ^ 0xC761C23C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[1]))
                    # tmp2 = val >> 19
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[2]+os, tmp_val_vec[2]+os, hash_val3_const_vec[1]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1], hash_val3_const_vec[0], tmp_val_vec[1], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3], hash_val3_const_vec[0], tmp_val_vec[3], hash_val1_const_vec[0]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[1]+2][2], merge_node_vec[merge_vec_idx[1]+0][2]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+3][2], valMod2_vec_level[0][2], node_val_preload_vec[14], node_val_preload_vec[10]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[3]+os, tmp_val_vec[3]+os, hash_val3_const_vec[1]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+3][2], merge_node_vec[merge_vec_idx[1]+3][2], merge_node_vec[merge_vec_idx[1]+1][2]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+0][1], valMod2_vec_level[0][1], node_val_preload_vec[11], node_val_preload_vec[7]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    # 3: val = ( val + 0x165667B1 ) + ( val << 5 ) = 33 * val + 0x165667B1
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[2], tmp_val_vec[0], hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[2], tmp_val_vec[2], hash_val1_const_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp1_vec[3]+os, tmp2_vec[3]+os))
                    # idx = (2 * idx + 1) + val%2
                    instr["valu"].append(("multiply_add", tmp_idx_vec[1], tmp_idx_vec[1], two_const_vec, valMod2_vec_level[1][1]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[3], tmp_idx_vec[3], two_const_vec, valMod2_vec_level[1][3]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+1][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[1]+3][2], merge_node_vec[merge_vec_idx[1]+1][2]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+2][1], valMod2_vec_level[0][1], node_val_preload_vec[13], node_val_preload_vec[9]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    # 4: val = ( val + 0xD3A2646C ) ^ ( val << 9 )
                    # tmp1 = val + 0xD3A2646C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("+", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[3]))
                    # tmp2 = val << 9
                    instr["valu"].append(("<<", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[3]))
                    for os in range(0,8):
                        instr["alu"].append(("<<", tmp2_vec[2]+os, tmp_val_vec[2]+os, hash_val3_const_vec[3]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1], hash_val3_const_vec[2], tmp_val_vec[1], hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3], hash_val3_const_vec[2], tmp_val_vec[3], hash_val1_const_vec[2]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+2][1], merge_node_vec[merge_vec_idx[1]+2][1], merge_node_vec[merge_vec_idx[1]+0][1]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+1][1], valMod2_vec_level[0][1], node_val_preload_vec[12], node_val_preload_vec[8]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("+", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[3]))
                    for os in range(0,8):
                        instr["alu"].append(("<<", tmp2_vec[3]+os, tmp_val_vec[3]+os, hash_val3_const_vec[3]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[1]+2][1], merge_node_vec[merge_vec_idx[1]+0][1]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+3][1], valMod2_vec_level[0][1], node_val_preload_vec[14], node_val_preload_vec[10]))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    # 5: val = ( val + 0xFD7046C5 ) + ( val << 3 ) = 9 * val + 0xFD7046C5
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[4], tmp_val_vec[0], hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[4], tmp_val_vec[2], hash_val1_const_vec[4]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp1_vec[3]+os, tmp2_vec[3]+os))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+3][1], merge_node_vec[merge_vec_idx[1]+3][1], merge_node_vec[merge_vec_idx[1]+1][1]))
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+1][2], merge_node_vec[merge_vec_idx[1]+1][2], merge_node_vec[merge_vec_idx[1]+0][2]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+0][3], valMod2_vec_level[0][3], node_val_preload_vec[11], node_val_preload_vec[7]))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    # 6: val = ( val ^ 0xB55A4F09 ) ^ ( val >> 16 )
                    # tmp1 = val ^ 0xB55A4F09
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[5]))
                    # tmp2 = val >> 16
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[5]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[2]+os, tmp_val_vec[2]+os, hash_val3_const_vec[5]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1], hash_val3_const_vec[4], tmp_val_vec[1], hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3], hash_val3_const_vec[4], tmp_val_vec[3], hash_val1_const_vec[4]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+1][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[1]+3][1], merge_node_vec[merge_vec_idx[1]+1][1]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+2][3], valMod2_vec_level[0][3], node_val_preload_vec[13], node_val_preload_vec[9]))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[5]))
                    for os in range(0,8):
                        instr["alu"].append((">>", tmp2_vec[3]+os, tmp_val_vec[3]+os, hash_val3_const_vec[5]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+2][3], merge_node_vec[merge_vec_idx[1]+2][3], merge_node_vec[merge_vec_idx[1]+0][3]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+1][3], valMod2_vec_level[0][3], node_val_preload_vec[12], node_val_preload_vec[8]))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("%", valMod2_vec_level[2][0], tmp_val_vec[0], two_const_vec))
                    instr["valu"].append(("%", valMod2_vec_level[2][2], tmp_val_vec[2], two_const_vec))
                    # instr 1,3 shifted
                    instr["valu"].append(("^", tmp_val_vec[1], tmp1_vec[1], tmp2_vec[1]))
                    for os in range(0,8):
                        instr["alu"].append(("^", tmp_val_vec[3]+os, tmp1_vec[3]+os, tmp2_vec[3]+os))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[1]+2][3], merge_node_vec[merge_vec_idx[1]+0][3]))
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+1][1], merge_node_vec[merge_vec_idx[1]+1][1], merge_node_vec[merge_vec_idx[1]+0][1]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+3][3], valMod2_vec_level[0][3], node_val_preload_vec[14], node_val_preload_vec[10]))
                    # preprocess node_val picking for level 4
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("%", valMod2_vec_level[2][1], tmp_val_vec[1], two_const_vec))
                    instr["valu"].append(("%", valMod2_vec_level[2][3], tmp_val_vec[3], two_const_vec))
                    # preprocess index picking for level 2
                    instr["valu"].append(("multiply_add", tmp_idx_vec[0], tmp_idx_vec[0], two_const_vec, valMod2_vec_level[2][0]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[2], tmp_idx_vec[2], two_const_vec, valMod2_vec_level[2][2]))
                    # preprocess node_val picking for level 2
                    instr["valu"].append(("multiply_add", node_val_vec[0], valMod2_vec_level[2][0], merge_node_vec[merge_vec_idx[1]+1][0], merge_node_vec[merge_vec_idx[1]+0][0]))
                    instr["valu"].append(("multiply_add", node_val_vec[2], valMod2_vec_level[2][2] ,merge_node_vec[merge_vec_idx[1]+1][2], merge_node_vec[merge_vec_idx[1]+0][2]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+1][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[1]+3][3], merge_node_vec[merge_vec_idx[1]+1][3]))
                    # preprocess node_val picking for level 3
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_idx_vec[1], tmp_idx_vec[1], two_const_vec, valMod2_vec_level[2][1]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[3], tmp_idx_vec[3], two_const_vec, valMod2_vec_level[2][3]))
                    instr["valu"].append(("multiply_add", load_addr_vec[addr_idx][0], tmp_idx_vec[0], two_const_vec, node_val_addr_minus_one_vec))
                    instr["valu"].append(("multiply_add", load_addr_vec[addr_idx][2], tmp_idx_vec[2], two_const_vec, node_val_addr_minus_one_vec))
                    instr["valu"].append(("-", merge_node_vec[merge_vec_idx[1]+1][3], merge_node_vec[merge_vec_idx[1]+1][3], merge_node_vec[merge_vec_idx[1]+0][3]))
                    body.append(instr)
                    # node_val = next_node_val1 + (val%2) * (next_node_val2 - next_node_val1)
                # all other rounds
                else:
                    # val = myhash(val ^ node_val) - vectorized for all 8 elements 
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp_val_vec[0], node_val_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp_val_vec[2], node_val_vec[2]))
                    if level == 3:
                        instr["valu"].append(("multiply_add", node_val_vec[1], valMod2_vec_level[2][1], merge_node_vec[merge_vec_idx[1]+1][1], merge_node_vec[merge_vec_idx[1]+0][1]))
                        instr["valu"].append(("multiply_add", node_val_vec[3], valMod2_vec_level[2][3], merge_node_vec[merge_vec_idx[1]+1][3], merge_node_vec[merge_vec_idx[1]+0][3]))
                        instr["valu"].append(("multiply_add", load_addr_vec[addr_idx][1], tmp_idx_vec[1], two_const_vec, node_val_addr_minus_one_vec))
                        instr["valu"].append(("multiply_add", load_addr_vec[addr_idx][3], tmp_idx_vec[3], two_const_vec, node_val_addr_minus_one_vec))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload", tmp3, load_addr_vec[addr_idx][0]))
                    instr["load"].append(("vload", tmp4, load_addr_vec[addr_idx][0]+1))
                    body.append(instr)

                    # hash #
                    # 1: val = (val + 0x7ED55D16) + (val << 12) = 4097 * val + 0x7ED55D16
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[0], tmp_val_vec[0], hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[0], tmp_val_vec[2], hash_val1_const_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[1], tmp_val_vec[1], node_val_vec[1]))
                    instr["valu"].append(("^", tmp_val_vec[3], tmp_val_vec[3], node_val_vec[3]))
                    # idx = (2 * idx + 1) + val%2
                    instr["alu"].append(("+", next_node_val[0][0], tmp3, zero_const))
                    instr["alu"].append(("+", next_node_val[1][0], tmp3+1, zero_const))
                    instr["alu"].append(("+", next_node_val[0][0]+1, tmp4, zero_const))
                    instr["alu"].append(("+", next_node_val[1][0]+1, tmp4+1, zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][0]+2))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][0]+3))
                    body.append(instr)

                    # 2: val = ( val ^ 0xC761C23C ) ^ (val >> 19)
                    # tmp1 = val ^ 0xC761C23C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[1]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[1]))
                    # tmp2 = val >> 19
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[1]))
                    instr["valu"].append(("multiply_add",tmp_val_vec[1],hash_val3_const_vec[0],tmp_val_vec[1],hash_val1_const_vec[0]))
                    instr["valu"].append(("multiply_add",tmp_val_vec[3],hash_val3_const_vec[0],tmp_val_vec[3],hash_val1_const_vec[0]))
                    instr["alu"].append(("+",next_node_val[0][0]+2,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][0]+2,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][0]+3,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][0]+3,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][0]+4))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][0]+5))
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^",tmp1_vec[1],tmp_val_vec[1],hash_val1_const_vec[1]))
                    instr["valu"].append(("^",tmp1_vec[3],tmp_val_vec[3],hash_val1_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[1]))
                    instr["valu"].append((">>", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[1]))
                    instr["alu"].append(("+",next_node_val[0][0]+4,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][0]+4,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][0]+5,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][0]+5,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][0]+6))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][0]+7))
                    body.append(instr)

                    # 3: val = ( val + 0x165667B1 ) + ( val << 5 ) = 33 * val + 0x165667B1
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[2], tmp_val_vec[0], hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[2], hash_val3_const_vec[2], tmp_val_vec[2], hash_val1_const_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^",tmp_val_vec[1],tmp1_vec[1],tmp2_vec[1]))
                    instr["valu"].append(("^",tmp_val_vec[3],tmp1_vec[3],tmp2_vec[3]))
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][0], four_const_vec, tmp_idx_vec[0], node_val_addr_minus_one_vec))
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][2], four_const_vec, tmp_idx_vec[2], node_val_addr_minus_one_vec))
                    instr["alu"].append(("+",next_node_val[0][0]+6,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][0]+6,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][0]+7,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][0]+7,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][2]))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][2]+1))
                    body.append(instr)

                    # 4: val = ( val + 0xD3A2646C ) ^ ( val << 9 )
                    # tmp1 = val + 0xD3A2646C
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("+", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[3]))
                    instr["valu"].append(("+", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[3]))
                    # tmp2 = val << 9
                    instr["valu"].append(("<<", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[3]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add", tmp_val_vec[1],hash_val3_const_vec[2],tmp_val_vec[1],hash_val1_const_vec[2]))
                    instr["valu"].append(("multiply_add", tmp_val_vec[3],hash_val3_const_vec[2],tmp_val_vec[3],hash_val1_const_vec[2]))
                    instr["alu"].append(("+",next_node_val[0][2],tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2],tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][2]+1,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2]+1,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][2]+2))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][2]+3))
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("+",tmp1_vec[1], tmp_val_vec[1], hash_val1_const_vec[3]))
                    instr["valu"].append(("+",tmp1_vec[3], tmp_val_vec[3], hash_val1_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[3]))
                    instr["valu"].append(("<<", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[3]))
                    instr["alu"].append(("+",next_node_val[0][2]+2,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2]+2,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][2]+3,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2]+3,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][2]+4))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][2]+5))
                    body.append(instr)

                    # 5: val = ( val + 0xFD7046C5 ) + ( val << 3 ) = 9 * val + 0xFD7046C5
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", tmp_val_vec[0], hash_val3_const_vec[4], tmp_val_vec[0], hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add",tmp_val_vec[2],hash_val3_const_vec[4],tmp_val_vec[2],hash_val1_const_vec[4]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^",tmp_val_vec[1],tmp1_vec[1],tmp2_vec[1]))
                    instr["valu"].append(("^",tmp_val_vec[3],tmp1_vec[3],tmp2_vec[3]))
                    instr["alu"].append(("+",next_node_val[0][2]+4,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2]+4,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][2]+5,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2]+5,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][2]+6))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][2]+7))
                    body.append(instr)

                    # 6: val = ( val ^ 0xB55A4F09 ) ^ ( val >> 16 )
                    # tmp1 = val ^ 0xB55A4F09
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp1_vec[0], tmp_val_vec[0], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[2], tmp_val_vec[2], hash_val1_const_vec[5]))
                    # tmp2 = val >> 16
                    instr["valu"].append((">>", tmp2_vec[0], tmp_val_vec[0], hash_val3_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[2], tmp_val_vec[2], hash_val3_const_vec[5]))
                    # instr 1,3 shifted
                    instr["valu"].append(("multiply_add",tmp_val_vec[1],hash_val3_const_vec[4],tmp_val_vec[1],hash_val1_const_vec[4]))
                    instr["valu"].append(("multiply_add",tmp_val_vec[3],hash_val3_const_vec[4],tmp_val_vec[3],hash_val1_const_vec[4]))
                    instr["alu"].append(("+",next_node_val[0][2]+6,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2]+6,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][2]+7,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][2]+7,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][1]))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][1]+1))
                    body.append(instr)

                    # val = tmp1 ^ tmp2
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("^", tmp_val_vec[0], tmp1_vec[0], tmp2_vec[0]))
                    instr["valu"].append(("^", tmp_val_vec[2], tmp1_vec[2], tmp2_vec[2]))
                    # instr 1,3 shifted
                    instr["valu"].append(("^",tmp1_vec[1],tmp_val_vec[1],hash_val1_const_vec[5]))
                    instr["valu"].append(("^",tmp1_vec[3],tmp_val_vec[3],hash_val1_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[1], tmp_val_vec[1], hash_val3_const_vec[5]))
                    instr["valu"].append((">>", tmp2_vec[3], tmp_val_vec[3], hash_val3_const_vec[5]))
                    instr["alu"].append(("+",next_node_val[0][1],tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1],tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][1]+1,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1]+1,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][1]+2))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][1]+3))
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    # instr 1,3 shifted
                    instr["valu"].append(("^",tmp_val_vec[1],tmp1_vec[1],tmp2_vec[1]))
                    instr["valu"].append(("^",tmp_val_vec[3],tmp1_vec[3],tmp2_vec[3]))
                    # no need to continue if it is the last round
                    if round == rounds - 1:
                        continue

                    instr["valu"].append(("%",valMod2_vec_level[0][0], tmp_val_vec[0], two_const_vec))
                    instr["valu"].append(("%",valMod2_vec_level[0][2], tmp_val_vec[2], two_const_vec))
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][1], four_const_vec, tmp_idx_vec[1], node_val_addr_minus_one_vec))
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][3], four_const_vec, tmp_idx_vec[3], node_val_addr_minus_one_vec))
                    instr["alu"].append(("+",next_node_val[0][1]+2,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1]+2,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][1]+3,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1]+3,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][1]+4))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][1]+5))
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("%",valMod2_vec_level[0][1], tmp_val_vec[1], two_const_vec))
                    instr["valu"].append(("%",valMod2_vec_level[0][3], tmp_val_vec[3], two_const_vec))
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][0], valMod2_vec_level[0][0], two_const_vec, load_addr_vec[1-addr_idx][0]))
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][2], valMod2_vec_level[0][2], two_const_vec, load_addr_vec[1-addr_idx][2]))
                    # idx = (2 * idx + 1) + val%2
                    instr["valu"].append(("multiply_add", tmp_idx_vec[0], two_const_vec, tmp_idx_vec[0], valMod2_vec_level[0][0]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[2], two_const_vec, tmp_idx_vec[2], valMod2_vec_level[0][2]))
                    instr["alu"].append(("+",next_node_val[0][1]+4,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1]+4,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][1]+5,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1]+5,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][1]+6))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][1]+7))
                    # with previous round idx, we can preload node_values at 2*idx + 1 and 2*idx+2
                    # once val%2 is determined, we can choose to pick which node_values
                    instr["flow"].append(("vselect", node_val_vec[0], valMod2_vec_level[0][0], next_node_val[1][0], next_node_val[0][0]))
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][1], valMod2_vec_level[0][1], two_const_vec, load_addr_vec[1-addr_idx][1]))
                    instr["valu"].append(("multiply_add", load_addr_vec[1-addr_idx][3], valMod2_vec_level[0][3], two_const_vec, load_addr_vec[1-addr_idx][3]))
                    # idx = (2 * idx + 1) + val%2
                    instr["valu"].append(("multiply_add", tmp_idx_vec[1], two_const_vec, tmp_idx_vec[1], valMod2_vec_level[0][1]))
                    instr["valu"].append(("multiply_add", tmp_idx_vec[3], two_const_vec, tmp_idx_vec[3], valMod2_vec_level[0][3]))
                    instr["alu"].append(("+",next_node_val[0][1]+6,tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1]+6,tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][1]+7,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][1]+7,tmp4+1,zero_const))
                    for os in range(2,8):
                        instr["alu"].append(("+",load_addr_vec[addr_idx][3]+os,load_addr_vec[addr_idx][3]+os,valMod2_vec_level[0][3]+os))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("vload",tmp3,load_addr_vec[addr_idx][3]))
                    instr["load"].append(("vload",tmp4,load_addr_vec[addr_idx][3]+1))
                    instr["flow"].append(("vselect", node_val_vec[2], valMod2_vec_level[0][2], next_node_val[1][2], next_node_val[0][2]))
                    body.append(instr)

                    # val%2 can be calculated in the same cycle of calculating val
                    # val%2 == (prev_val%2)<<16 == (prev_val & 1 << 16)
                    # pre-calculate has no benefit when 4 vec combined into single instruction flow due to slot limit
                    # one cycle delay on calculating val%2 is always there
                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    # next_idx = 2 * idx + [1:2]
                    instr["alu"].append(("+",next_node_val[0][3],tmp3,zero_const))
                    instr["alu"].append(("+",next_node_val[1][3],tmp3+1,zero_const))
                    instr["alu"].append(("+",next_node_val[0][3]+1,tmp4,zero_const))
                    instr["alu"].append(("+",next_node_val[1][3]+1,tmp4+1,zero_const))
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("load",node_val_vec[3]+2,load_addr_vec[addr_idx][3]+2))
                    instr["load"].append(("load",node_val_vec[3]+3,load_addr_vec[addr_idx][3]+3))
                    instr["flow"].append(("vselect", node_val_vec[1], valMod2_vec_level[0][1], next_node_val[1][1], next_node_val[0][1]))
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("load",node_val_vec[3]+4,load_addr_vec[addr_idx][3]+4))
                    instr["load"].append(("load",node_val_vec[3]+5,load_addr_vec[addr_idx][3]+5))
                    instr["flow"].append(("select", node_val_vec[3], valMod2_vec_level[0][3], next_node_val[1][3], next_node_val[0][3]))
                    body.append(instr)

                    instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
                    # next_node_val = node_val[next_addr]
                    instr["load"].append(("load",node_val_vec[3]+6,load_addr_vec[addr_idx][3]+6))
                    instr["load"].append(("load",node_val_vec[3]+7,load_addr_vec[addr_idx][3]+7))
                    instr["flow"].append(("select", node_val_vec[3]+1, valMod2_vec_level[0][3]+1, next_node_val[1][3]+1, next_node_val[0][3]+1))
                    body.append(instr)

                    addr_idx = (1-addr_idx)
                    # node_val = next_node_val1 + (val%2) * (next_node_val2 - next_node_val1)

            # mem[inp_values_p + i] = val
            instr["store"].append(("vstore", store_load_val_addr_vec[0], tmp_val_vec[0]))
            instr["store"].append(("vstore", store_load_val_addr_vec[2], tmp_val_vec[2]))
            if i != batch_size - batch_load_size * VLEN :
                instr["load"].append(("vload", tmp_val_vec[0], next_store_load_val_addr_vec[0]))
                instr["load"].append(("vload",tmp_val_vec[2],next_store_load_val_addr_vec[2]))
                instr["alu"].append(("+",store_load_val_addr_vec[0],next_store_load_val_addr_vec[0],zero_const))
                instr["alu"].append(("+",store_load_val_addr_vec[2],next_store_load_val_addr_vec[2],zero_const))
                instr["valu"].append(("vbroadcast",node_val_vec[0],const_node_val_vec))
                instr["valu"].append(("vbroadcast",node_val_vec[1],const_node_val_vec))
                for os in range(0,8):
                    instr["alu"].append(("+",node_val_vec[2]+os,const_node_val_vec,zero_const))
                instr["alu"].append(("+",node_val_vec[3],const_node_val_vec,zero_const))
                instr["alu"].append(("+",node_val_vec[3]+1,const_node_val_vec,zero_const))
            body.append(instr)
            instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
            instr["store"].append(("vstore", store_load_val_addr_vec[1], tmp_val_vec[1]))
            instr["store"].append(("vstore", store_load_val_addr_vec[3], tmp_val_vec[3]))
            if i != batch_size - batch_load_size * VLEN :
                instr["load"].append(("vload", tmp_val_vec[1], next_store_load_val_addr_vec[1]))
                instr["load"].append(("vload", tmp_val_vec[3], next_store_load_val_addr_vec[3]))
                instr["alu"].append(("+",next_store_load_val_addr_vec[0],store_load_val_addr_vec[0],batch_stride))
                instr["alu"].append(("+",next_store_load_val_addr_vec[2],store_load_val_addr_vec[2],batch_stride))
                instr["alu"].append(("+",next_store_load_val_addr_vec[1],next_store_load_val_addr_vec[1],batch_stride))
                instr["alu"].append(("+",next_store_load_val_addr_vec[3],next_store_load_val_addr_vec[3],batch_stride))
                instr["alu"].append(("+",store_load_val_addr_vec[1],next_store_load_val_addr_vec[1],zero_const))
                instr["alu"].append(("+",store_load_val_addr_vec[3],next_store_load_val_addr_vec[3],zero_const))
                instr["alu"].append(("+",node_val_vec[3]+2,const_node_val_vec,zero_const))
                instr["alu"].append(("+",node_val_vec[3]+3,const_node_val_vec,zero_const))
                instr["alu"].append(("+",node_val_vec[3]+4,const_node_val_vec,zero_const))
                instr["alu"].append(("+",node_val_vec[3]+5,const_node_val_vec,zero_const))
                instr["alu"].append(("+",node_val_vec[3]+6,const_node_val_vec,zero_const))
                instr["alu"].append(("+",node_val_vec[3]+7,const_node_val_vec,zero_const))
                # pre calculate tmp_val = tmp_val ^ node_val[0]
                instr["valu"].append(("^",tmp_val_vec[0],tmp_val_vec[0],node_val_preload_vec[0]))
                instr["valu"].append(("^",tmp_val_vec[2],tmp_val_vec[2],node_val_preload_vec[0]))
            body.append(instr)

        body_instrs = self.build(body, vliw=True)
        #body_instrs = self.build(body)
        self.instrs.extend(body_instrs)
        # Required to match with the yield in reference_kernel2
        self.instrs.append({"flow": [("pause",)]})

BASELINE = 147734

def do_kernel_test(
    forest_height: int,
    rounds: int,
    batch_size: int,
    seed: int = 123,
    trace: bool = False,
    prints: bool = False,
):
    print(f"{forest_height=}, {rounds=}, {batch_size=}")
    random.seed(seed)
    forest = Tree.generate(forest_height)
    inp = Input.generate(forest, batch_size, rounds)
    mem = build_mem_image(forest, inp)

    kb = KernelBuilder()
    kb.build_kernel(forest.height, len(forest.values), len(inp.indices), rounds)
    # print(kb.instrs)

    value_trace = {}
    machine = Machine(
        mem,
        kb.instrs,
        kb.debug_info(),
        n_cores=N_CORES,
        value_trace=value_trace,
        trace=trace,
    )
    machine.prints = prints
    for i, ref_mem in enumerate(reference_kernel2(mem, value_trace)):
        machine.run()
        inp_values_p = ref_mem[6]
        for j in range(len(inp.values)):
            if ( (machine.mem[inp_values_p + j] != ref_mem[inp_values_p + j] )):
            #if j == 0 or (j > 30 and j < 42) :
            #if prints:
                print("i=",i,"j=",j,"tar mem = ",machine.mem[inp_values_p + j]," ref mem = ",ref_mem[inp_values_p + j])
                #print(machine.mem[inp_values_p + j])
                #print(ref_mem[inp_values_p + j])
        assert (
            machine.mem[inp_values_p : inp_values_p + len(inp.values)]
            == ref_mem[inp_values_p : inp_values_p + len(inp.values)]
        ), f"Incorrect result on round {i}"
        inp_indices_p = ref_mem[5]
        #if prints:
        #    print(machine.mem[inp_indices_p : inp_indices_p + len(inp.indices)])
        #    print(ref_mem[inp_indices_p : inp_indices_p + len(inp.indices)])
        # Updating these in memory isn't required, but you can enable this check for debugging
        # assert machine.mem[inp_indices_p:inp_indices_p+len(inp.indices)] == ref_mem[inp_indices_p:inp_indices_p+len(inp.indices)]

    print("CYCLES: ", machine.cycle)
    print("USED scratch memory: ",kb.scratch_ptr)
    print("Speedup over baseline: ", BASELINE / machine.cycle)
    return machine.cycle


class Tests(unittest.TestCase):
    def test_ref_kernels(self):
        """
        Test the reference kernels against each other
        """
        random.seed(123)
        for i in range(10):
            f = Tree.generate(4)
            inp = Input.generate(f, 10, 6)
            mem = build_mem_image(f, inp)
            reference_kernel(f, inp)
            for _ in reference_kernel2(mem, {}):
                pass
            #assert inp.indices == mem[mem[5] : mem[5] + len(inp.indices)]
            assert inp.values == mem[mem[6] : mem[6] + len(inp.values)]

    def test_kernel_trace(self):
        # Full-scale example for performance testing
        do_kernel_test(10, 16, 256, trace=True, prints=False)

    # Passing this test is not required for submission, see submission_tests.py for the actual correctness test
    # You can uncomment this if you think it might help you debug
    # def test_kernel_correctness(self):
    #     for batch in range(1, 3):
    #         for forest_height in range(3):
    #             do_kernel_test(
    #                 forest_height + 2, forest_height + 4, batch * 16 * VLEN * N_CORES
    #             )

    def test_kernel_cycles(self):
        do_kernel_test(10, 16, 256)


# To run all the tests:
#    python perf_takehome.py
# To run a specific test:
#    python perf_takehome.py Tests.test_kernel_cycles
# To view a hot-reloading trace of all the instructions:  **Recommended debug loop**
# NOTE: The trace hot-reloading only works in Chrome. In the worst case if things aren't working, drag trace.json onto https://ui.perfetto.dev/
#    python perf_takehome.py Tests.test_kernel_trace
# Then run `python watch_trace.py` in another tab, it'll open a browser tab, then click "Open Perfetto"
# You can then keep that open and re-run the test to see a new trace.

# To run the proper checks to see which thresholds you pass:
#    python tests/submission_tests.py

if __name__ == "__main__":
    unittest.main()
