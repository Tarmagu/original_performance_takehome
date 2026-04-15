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

    def init_instr(self):
        return {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}

    def is_instr_empty( self, instr ):
        for name, slots in instr.items():
            if len(slots) != 0:
                return False
        return True
    
    def append_instr( self, body, instr ):
        for name, slots in instr.items():
            assert len(slots) <= SLOT_LIMITS[name]
        body.append(instr)
    
    def merge_instr( self, instr1:dict[str,list[tuple]], instr2:dict[str,list[tuple]], zero_const ):
        merged_instr = {}
        remaining_instr = {}
        # instr1 is always valid instr
        for key in instr1:
            if key in instr2:
                len1 = len(instr1[key])
                len2 = len(instr2[key])
                if len1 + len2 > SLOT_LIMITS[key]:
                    value = instr1[key] + instr2[key][0:SLOT_LIMITS[key]-len1]
                    remain_value = instr2[key][SLOT_LIMITS[key]-len1:]
                    remaining_instr.update({key:remain_value})
                else:
                    value = instr1[key] + instr2[key]
                merged_instr.update({key:value})
            else:
                merged_instr.update({key:instr1[key][:]})
        for key in instr2:
            if key not in merged_instr:
                len2 = len(instr2[key])
                if len2 > SLOT_LIMITS[key]:
                    value = instr2[key][0:SLOT_LIMITS[key]]
                    remain_value = instr2[key][SLOT_LIMITS[key]:]
                    remaining_instr.update({key:remain_value})
                else:
                    value = instr2[key][:]
                merged_instr.update({key:value})
        
        # transfer remaining instr if possible
        # valu ==> alu if valu is not multiply_add
        if len(remaining_instr) == 1:
            if "valu" in remaining_instr:
                if len(remaining_instr["valu"]) < 2:
                    slot = remaining_instr["valu"][0]
                    if slot[0] == "multiply_add":
                        for index,replace_slot in enumerate(merged_instr["valu"]):
                            if replace_slot[0] != "multiply_add":
                                merged_instr["valu"][index] = slot
                                slot = replace_slot
                                break
                                
                    alu_instr = []
                    if slot[0] != "multiply_add":
                        match slot:
                            case ("vbroadcast", dest, src ):
                                for os in range(8):
                                    alu_instr.append(("+", dest+os, src, zero_const))
                            case (op, dest, a1, a2):
                                for os in range(8):
                                    alu_instr.append((op, dest+os, a1+os, a2+os))
                            case _:
                                print(f"Invalid valu op {slot}")
                        merged_instr.update({"alu":alu_instr})
                        remaining_instr.clear()

        return merged_instr, remaining_instr

    def merge_batch( self, body1, body2, offset, zero_const, isDebug = False ):
        tot_len = max(len(body1), len(body2) + offset)
        merged_body = []
        for i in range(offset):
            self.append_instr( merged_body, body1[i] )
        
        if len(body1) < len(body2)+offset:
            for i in range(offset, len(body1)):
                merged_instr,remaining_instr = self.merge_instr(body1[i],body2[i-offset],zero_const)
                if len(remaining_instr) != 0:
                    print(f"failed to merge at {i}th instr")
                    print("main body instr is ", body1[i], " side body instr is ", body2[i-offset])
                    assert 0
                else:
                    self.append_instr( merged_body, merged_instr )
            for i in range(len(body1), tot_len):
                self.append_instr( merged_body, body2[i-offset] )
        else:
            for i in range(offset, len(body2)+offset):
                merged_instr,remaining_instr = self.merge_instr(body1[i],body2[i-offset],zero_const)
                if len(remaining_instr) != 0:
                    print(f"failed to merge at {i}th instr")
                    print("main body instr is ", body1[i], " side body instr is ", body2[i-offset])
                    assert 0
                else:
                    self.append_instr( merged_body, merged_instr )
            for i in range(len(body2)+offset, tot_len):
                self.append_instr( merged_body, body1[i] )
        
        body1[:] = merged_body
        if isDebug:
            print("merged body len:",len(body1))
            
    def merge_load( self, main_body, load_body:list[list[list[dict[str,list[tuple]]|int|list[int]]]], zero_const, isDebug ):
        if isDebug:
            print("main body len:", len(main_body))
        for round,load_level in enumerate(load_body):
            if len(load_level) == 0:
                continue
            orig_load_len = len(load_level)
            # add load slot into main body from back
            start_idx = -1
            in_degree = {}
            dependency_graph:dict[int,list[int]] = {}
            for instr_idx in range(len(load_level)):
                dependency_graph[instr_idx] = []
            available_slots = []
            added_slots = []
            next_slots = []
            avail_pos_idx = {"alu":0,"valu":1,"flow":2,"load":3,"store":4}
            avail_pos = [0,0,0,0,0]
            for instr_idx,load_body_slot in enumerate(load_level):
                if load_body_slot[2] > start_idx:
                    start_idx = load_body_slot[2]
                in_degree[instr_idx] = len(load_body_slot[3])
                for dep_instr_idx in load_body_slot[3]:
                    dependency_graph[dep_instr_idx].append(instr_idx)
            if start_idx < 0:
                continue
            # collect available_slots
            # available_slots should sort based on ops, "alu" < "valu" < "flow" < others
            for instr_idx, load_body_slot in enumerate(load_level):
                if load_body_slot[2] == start_idx:
                    slot = load_body_slot[0]
                    slot_op = next(iter(slot))
                    min_dep = min(load_body_slot[3]) if len(load_body_slot[3]) else -1
                    iter_start = avail_pos[avail_pos_idx[slot_op]]
                    iter_end = avail_pos[avail_pos_idx[slot_op]+1] if avail_pos_idx[slot_op] < 4 else iter_start+1
                    insert_idx = iter_start
                    for iter_idx in available_slots[iter_start:iter_end]:
                        iter_min_dep = min(load_level[iter_idx][3]) if len(load_level[iter_idx][3]) else -1
                        if min_dep > iter_min_dep:
                            break
                        if min_dep == iter_min_dep and instr_idx > iter_idx:
                            break
                        insert_idx += 1
                    available_slots.insert(insert_idx,instr_idx)
                    for idx in range(avail_pos_idx[slot_op]+1,5):
                        avail_pos[idx] += 1
            cur_idx= start_idx - 1
            if isDebug:
                print("Step debug dump round:", round, "start_idx:", start_idx, "inst #", cur_idx)
                for ops in avail_pos_idx:
                    print(ops,"size:", SLOT_LIMITS[ops]-len(main_body[cur_idx][ops]),":",main_body[cur_idx][ops])
                print("available slots")
                for instr_idx in available_slots:
                    print("#",instr_idx, load_level[instr_idx])
            while len(added_slots) < len(load_level):
                for avail_idx in available_slots[:]:
                    slot, min_idx, max_idx, dep_list = load_level[avail_idx]
                    # check if any violation
                    if max_idx > 0:
                        if cur_idx >= max_idx:
                            continue
                    if min_idx != -1:
                        if cur_idx <= min_idx:
                            print("Fail to merge at round ", round, " #", cur_idx, " start_idx = ", start_idx )
                            for i in range(max(0,cur_idx-5), start_idx):
                                remain_slots = {"alu":0,"valu":0,"flow":0,"load":0,"store":0}
                                for ops in remain_slots:
                                    remain_slots[ops] = SLOT_LIMITS[ops] - len(main_body[i][ops])
                                print("#", i, "remain:", remain_slots)
                                for ops in remain_slots:
                                    print(ops,":", main_body[i][ops])
                            print("load level: ")
                            for idx,load_level_slot in enumerate(load_level):
                                print( "#", idx, load_level_slot)
                            print("load slot: ", load_level[avail_idx])
                            assert 0
                    if len(dep_list):
                        assert set(dep_list).issubset(added_slots)
                    # add slot into main body
                    ops = next(iter(slot))
                    value = slot[ops]
                    # add to main body if spare space is available
                    if len(main_body[cur_idx][ops]) < SLOT_LIMITS[ops]:
                        main_body[cur_idx][ops].append(value[0])
                        # update in degree
                        for dep_instr_idx in dependency_graph[avail_idx]:
                            new_degree = in_degree[dep_instr_idx] -1
                            in_degree[dep_instr_idx] = new_degree
                            if new_degree == 0:
                                next_slots.append(dep_instr_idx)
                        # remove avail_idx from available_slots
                        available_slots.remove(avail_idx)
                        for idx in range(avail_pos_idx[ops]+1,5):
                            avail_pos[idx] -= 1
                        added_slots.append(avail_idx)
                    else:
                        # transfer {"flow":[("vselect",dest,cond,op1,op2)]} to
                        # {"valu":[("-",op1,op1,op2)]}
                        # {"valu":[("multiply_add",dest,cond,op1,op2)]}
                        if ops == "flow":
                            sub_ops, dest, cond, op1, op2 = value[0]
                            assert sub_ops == "vselect"
                            new_slot1 = ( "multiply_add", dest, cond, op1, op2 )
                            new_slot2 = ( "-", op1, op1, op2 )
                            can_add = False
                            # previous instr has spare space
                            if max_idx > -2 and orig_load_len > 5:
                                if len(main_body[cur_idx]["valu"]) < SLOT_LIMITS["valu"]:
                                    can_add = True
                                elif len(main_body[cur_idx]["alu"]) <= SLOT_LIMITS["alu"] - 8:
                                    for sub_slot in main_body[cur_idx]["valu"][:]:
                                        if sub_slot[0] != "multiply_add":
                                            can_add = True
                                            if sub_slot[0] == "vbroadcast":
                                                for os in range(8):
                                                    main_body[cur_idx]["alu"].append(("+",sub_slot[1]+os,sub_slot[2],zero_const))
                                            else:
                                                for os in range(8):
                                                    main_body[cur_idx]["alu"].append((sub_slot[0],sub_slot[1]+os,sub_slot[2]+os,sub_slot[3]+os))
                                            main_body[cur_idx]["valu"].remove(sub_slot)
                                            break
                                if can_add:
                                    main_body[cur_idx]["valu"].append(new_slot1)
                                    # remove avail_idx from available_slots
                                    available_slots.remove(avail_idx)
                                    for idx in range(avail_pos_idx[ops]+1,5):
                                        avail_pos[idx] -= 1
                                    added_slots.append(avail_idx)
                                    new_inst_idx = len(load_level)
                                    load_level.append([{"valu":[new_slot2]},-1,-1,[avail_idx]])
                                    load_level[avail_idx] = [{"valu":new_slot1},min_idx,max_idx,dep_list]
                                    dependency_graph[new_inst_idx] = dependency_graph[avail_idx]
                                    for dep_idx in dependency_graph[new_inst_idx]:
                                        load_level[dep_idx][3].remove(avail_idx)
                                        load_level[dep_idx][3].append(new_inst_idx)
                                    dependency_graph[avail_idx] = [new_inst_idx]
                                    in_degree[new_inst_idx] = 0
                                    next_slots.append(new_inst_idx)
                        elif (ops == "valu") and (len(main_body[cur_idx]["alu"]) <= SLOT_LIMITS["alu"] - 8):
                            # transfer "valu" to "alu"
                            if value[0][0] == "multiply_add":
                                for sub_slot in main_body[cur_idx]["valu"][:]:
                                    if sub_slot[0] != "multiply_add":
                                        if sub_slot[0] == "vbroadcast":
                                            for os in range(8):
                                                main_body[cur_idx]["alu"].append(("+",sub_slot[1]+os,sub_slot[2],zero_const))
                                        else:
                                            for os in range(8):
                                                main_body[cur_idx]["alu"].append((sub_slot[0],sub_slot[1]+os,sub_slot[2]+os,sub_slot[3]+os))
                                        main_body[cur_idx]["valu"].remove(sub_slot)
                                        main_body[cur_idx]["valu"].append(value[0])
                                        added_slots.append(avail_idx)
                                        available_slots.remove(avail_idx)
                                        for idx in range(avail_pos_idx[ops]+1,5):
                                            avail_pos[idx] -= 1
                                        # update in degree
                                        for dep_instr_idx in dependency_graph[avail_idx]:
                                            new_degree = in_degree[dep_instr_idx] -1
                                            in_degree[dep_instr_idx] = new_degree
                                            if new_degree == 0:
                                                next_slots.append(dep_instr_idx)
                                        break
                            else:
                                if value[0][0] == "vbroadcast":
                                    sub_ops, dest, src = value[0]
                                    for os in range(8):
                                        main_body[cur_idx]["alu"].append(("+",dest+os,src,zero_const))
                                else:
                                    sub_ops, dest, op1, op2 = value[0]
                                    for os in range(8):
                                        main_body[cur_idx]["alu"].append((sub_ops,dest+os,op1+os,op2+os))
                                added_slots.append(avail_idx)
                                available_slots.remove(avail_idx)
                                for idx in range(avail_pos_idx[ops]+1,5):
                                    avail_pos[idx] -= 1
                                # update in degree
                                for dep_instr_idx in dependency_graph[avail_idx]:
                                    new_degree = in_degree[dep_instr_idx] -1
                                    in_degree[dep_instr_idx] = new_degree
                                    if new_degree == 0:
                                        next_slots.append(dep_instr_idx)

                cur_idx -= 1
                # move next_slots to available_slots
                if len(next_slots) > 0:
                    for next_slot_idx in next_slots:
                        next_slot = load_level[next_slot_idx]
                        slot_op = next(iter((next_slot[0])))
                        min_dep = min(next_slot[3]) if len(next_slot[3]) else -1
                        if min_dep >= orig_load_len:
                            min_dep = min(load_level[min_dep][3])
                        iter_start = avail_pos[avail_pos_idx[slot_op]]
                        iter_end = avail_pos[avail_pos_idx[slot_op]+1] if avail_pos_idx[slot_op] < 4 else iter_start+1
                        insert_idx = iter_start
                        for iter_idx in available_slots[iter_start:iter_end]:
                            iter_min_dep = min(load_level[iter_idx][3]) if len(load_level[iter_idx][3]) else -1
                            if iter_min_dep >= orig_load_len:
                                iter_min_dep = min(load_level[iter_min_dep][3])
                            if min_dep > iter_min_dep:
                                break
                            if min_dep == iter_min_dep and (( next_slot_idx < orig_load_len and next_slot_idx > iter_idx) or ( next_slot_idx >= orig_load_len and next_slot_idx < iter_idx )):
                                break
                            insert_idx += 1
                        available_slots.insert(insert_idx,next_slot_idx)
                        for idx in range(avail_pos_idx[slot_op]+1,5):
                            avail_pos[idx] += 1
                    next_slots = []
                if isDebug:
                    print("Step debug dump round:", round, "start_idx:", start_idx, "inst #", cur_idx)
                    for ops in avail_pos_idx:
                        print(ops,"size:", SLOT_LIMITS[ops]-len(main_body[cur_idx][ops]),":",main_body[cur_idx][ops])
                    print("available slots")
                    for instr_idx in available_slots:
                        dep_idx = min(load_level[instr_idx][3])
                        if dep_idx >= orig_load_len:
                            next_dep_idx = min(load_level[dep_idx][3]) if len(load_level[dep_idx][3]) else -1
                            print("#",instr_idx, load_level[instr_idx],"->",next_dep_idx)
                        else:
                            print("#",instr_idx, load_level[instr_idx])
            if round == -1:
                print("round",round,"main body instr")
                for instr_idx in range(cur_idx, start_idx+1):
                    remain_slots = {"alu":0,"valu":0,"flow":0,"load":0,"store":0}
                    for ops in remain_slots:
                        remain_slots[ops] = SLOT_LIMITS[ops] - len(main_body[instr_idx][ops])
                    print("#", instr_idx, "remain:", remain_slots)
                    for ops in remain_slots:
                        print(ops,":", main_body[instr_idx][ops])
                print("load level: ")
                for idx,load_slot in enumerate(load_level):
                    print("load #",idx, load_slot)



    def generate_load_instrs( self, rounds, height, batch_idx, round, level,
                              next_node_val_vec, mod2_level_vec, node_val_preload_vec,
                              tmp_load_vec, load_addr_vec, tmp_vec,
                              idx_vec, node_val_addr_minus_one_vec, two_const_vec, zero_const,
                              mod2_ready_vec, final_required_idx )->list[list[dict[str,list[tuple]]|int|list[int]]]:
        # each entry of load body is a list of one level's load instruction
        # each entry is [slot, required_after_line_num, required_before_line_num, required_by_instr_idx ]
        load_body = []
        if (level == 0) or (round == rounds-1) or (level==height):
            # nothing to load for level 0, height or rounds-1
            return load_body
        elif level == 1:
            # idx 0
            slot = {"valu":[("multiply_add", next_node_val_vec[0][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[5], node_val_preload_vec[3])]}
            load_body.append( [ slot, mod2_ready_vec[0], -1, [4]])
            # idx 1
            slot = {"valu":[("multiply_add", next_node_val_vec[0][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[5], node_val_preload_vec[3])]}
            load_body.append( [ slot, mod2_ready_vec[0], final_required_idx, []])
            # idx 2
            slot = {"flow":[("vselect", next_node_val_vec[1][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[6], node_val_preload_vec[4])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [4]])
            # idx 3
            slot = {"flow":[("vselect", next_node_val_vec[1][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[6], node_val_preload_vec[4])]}
            load_body.append( [ slot, mod2_ready_vec[0], final_required_idx, []])
            # idx 4
            slot = {"valu":[("-", next_node_val_vec[1][batch_idx[0]], next_node_val_vec[1][batch_idx[0]], next_node_val_vec[0][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[0], final_required_idx, []])
            # batch_idx[1] is using vselect so subtract is not needed
        elif level == 2:
            # idx 0
            slot = { "flow":[("vselect", tmp_load_vec[0][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[11], node_val_preload_vec[7])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [8]])
            # idx 1
            slot = { "flow":[("vselect", tmp_load_vec[0][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[11], node_val_preload_vec[7])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [10]])
            # idx 2
            slot = { "flow":[("vselect", tmp_load_vec[1][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[12], node_val_preload_vec[8])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [9]])
            # idx 3
            slot = { "flow":[("vselect", tmp_load_vec[1][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[12], node_val_preload_vec[8])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [11]])
            # idx 4
            slot = { "flow":[("vselect", tmp_load_vec[2][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[13], node_val_preload_vec[9])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [8]])
            # idx 5
            slot = { "flow":[("vselect", tmp_load_vec[2][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[13], node_val_preload_vec[9])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [10]])
            # idx 6
            slot = { "flow":[("vselect", tmp_load_vec[3][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[14], node_val_preload_vec[10])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [9]])
            # idx 7
            slot = { "flow":[("vselect", tmp_load_vec[3][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[14], node_val_preload_vec[10])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [11]])
            # idx 8
            slot = { "flow":[("vselect", next_node_val_vec[0][batch_idx[0]], mod2_level_vec[1][batch_idx[0]], tmp_load_vec[2][batch_idx[0]], tmp_load_vec[0][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [12]])
            # idx 9
            slot = { "flow":[("vselect", next_node_val_vec[1][batch_idx[0]], mod2_level_vec[1][batch_idx[0]], tmp_load_vec[3][batch_idx[0]], tmp_load_vec[1][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [12]])
            # idx 10
            slot = { "flow":[("vselect", next_node_val_vec[0][batch_idx[1]], mod2_level_vec[1][batch_idx[1]], tmp_load_vec[2][batch_idx[1]], tmp_load_vec[0][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[1], final_required_idx, []])
            # idx 11
            slot = { "flow":[("vselect", next_node_val_vec[1][batch_idx[1]], mod2_level_vec[1][batch_idx[1]], tmp_load_vec[3][batch_idx[1]], tmp_load_vec[1][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[1], final_required_idx, []])
            # idx 12
            slot = { "valu":[("-", next_node_val_vec[1][batch_idx[0]], next_node_val_vec[1][batch_idx[0]], next_node_val_vec[0][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[1], final_required_idx, []])
            # batch_idx[1] is using vselect so subtract is not needed
        elif round == 14:
            # idx 0
            slot ={"flow":[("vselect", tmp_load_vec[4][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[23], node_val_preload_vec[15])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [16]])
            # idx 1
            slot ={"flow":[("vselect", tmp_load_vec[4][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[23], node_val_preload_vec[15])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [20]])
            # idx 2
            slot ={"flow":[("vselect", tmp_load_vec[5][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[24], node_val_preload_vec[16])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [17]])
            # idx 3
            slot ={"flow":[("vselect", tmp_load_vec[5][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[24], node_val_preload_vec[16])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [21]])
            # idx 4
            slot ={"flow":[("vselect", tmp_load_vec[6][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[25], node_val_preload_vec[17])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [18]])
            # idx 5
            slot ={"flow":[("vselect", tmp_load_vec[6][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[25], node_val_preload_vec[17])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [22]])
            # idx 6
            slot ={"valu":[("multiply_add", tmp_load_vec[7][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[26], node_val_preload_vec[18])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [19]])
            # idx 7
            slot ={"valu":[("multiply_add", tmp_load_vec[7][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[26], node_val_preload_vec[18])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [23]])
            # idx 8
            slot ={"valu":[("multiply_add", tmp_load_vec[8][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[27], node_val_preload_vec[19])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [16]])
            # idx 9
            slot ={"valu":[("multiply_add", tmp_load_vec[8][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[27], node_val_preload_vec[19])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [20]])
            # idx 10
            slot ={"valu":[("multiply_add", tmp_load_vec[9][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[28], node_val_preload_vec[20])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [17]])
            # idx 11
            slot ={"valu":[("multiply_add", tmp_load_vec[9][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[28], node_val_preload_vec[20])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [21]])
            # idx 12
            slot ={"valu":[("multiply_add", tmp_load_vec[10][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[29], node_val_preload_vec[21])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [18]])
            # idx 13
            slot ={"valu":[("multiply_add", tmp_load_vec[10][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[29], node_val_preload_vec[21])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [22]])
            # idx 14
            slot ={"valu":[("multiply_add", tmp_load_vec[11][batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[30], node_val_preload_vec[22])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [19]])
            # idx 15
            slot ={"valu":[("multiply_add", tmp_load_vec[11][batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[30], node_val_preload_vec[22])]}
            load_body.append( [ slot, mod2_ready_vec[0], -2, [23]])
            # idx 16
            slot ={"flow":[("vselect", tmp_load_vec[4][batch_idx[0]], mod2_level_vec[1][batch_idx[0]], tmp_load_vec[8][batch_idx[0]], tmp_load_vec[4][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [24]])
            # idx 17
            slot ={"flow":[("vselect", tmp_load_vec[5][batch_idx[0]], mod2_level_vec[1][batch_idx[0]], tmp_load_vec[9][batch_idx[0]], tmp_load_vec[5][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [25]])
            # idx 18
            slot ={"flow":[("vselect", tmp_load_vec[6][batch_idx[0]], mod2_level_vec[1][batch_idx[0]], tmp_load_vec[10][batch_idx[0]], tmp_load_vec[6][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [24]])
            # idx 19
            slot ={"flow":[("vselect", tmp_load_vec[7][batch_idx[0]], mod2_level_vec[1][batch_idx[0]], tmp_load_vec[11][batch_idx[0]], tmp_load_vec[7][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [25]])
            # idx 20
            slot ={"flow":[("vselect", tmp_load_vec[4][batch_idx[1]], mod2_level_vec[1][batch_idx[1]], tmp_load_vec[8][batch_idx[1]], tmp_load_vec[4][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [26]])
            # idx 21
            slot ={"flow":[("vselect", tmp_load_vec[5][batch_idx[1]], mod2_level_vec[1][batch_idx[1]], tmp_load_vec[9][batch_idx[1]], tmp_load_vec[5][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [27]])
            # idx 22
            slot ={"flow":[("vselect", tmp_load_vec[6][batch_idx[1]], mod2_level_vec[1][batch_idx[1]], tmp_load_vec[10][batch_idx[1]], tmp_load_vec[6][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [26]])
            # idx 23
            slot ={"flow":[("vselect", tmp_load_vec[7][batch_idx[1]], mod2_level_vec[1][batch_idx[1]], tmp_load_vec[11][batch_idx[1]], tmp_load_vec[7][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[1], -1, [27]])
            # idx 24
            slot = {"flow":[("vselect", next_node_val_vec[0][batch_idx[0]], mod2_level_vec[2][batch_idx[0]], tmp_load_vec[6][batch_idx[0]], tmp_load_vec[4][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[2], -1, [28]])
            # idx 25
            slot = {"flow":[("vselect", next_node_val_vec[1][batch_idx[0]], mod2_level_vec[2][batch_idx[0]], tmp_load_vec[7][batch_idx[0]], tmp_load_vec[5][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[2], -1, [28]])
            # idx 26
            slot = {"flow":[("vselect", next_node_val_vec[0][batch_idx[1]], mod2_level_vec[2][batch_idx[1]], tmp_load_vec[6][batch_idx[1]], tmp_load_vec[4][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[2], final_required_idx, []])
            # idx 27
            slot = {"flow":[("vselect", next_node_val_vec[1][batch_idx[1]], mod2_level_vec[2][batch_idx[1]], tmp_load_vec[7][batch_idx[1]], tmp_load_vec[5][batch_idx[1]])]}
            load_body.append( [ slot, mod2_ready_vec[2], final_required_idx, []])
            # idx 28
            slot = {"valu":[("-", next_node_val_vec[1][batch_idx[0]], next_node_val_vec[1][batch_idx[0]], next_node_val_vec[0][batch_idx[0]])]}
            load_body.append( [ slot, mod2_ready_vec[2], final_required_idx, []])
            # batch_idx[1] is using vselect so subtract is not needed
        # round > 2 and round < 10
        else:
            # idx 0
            slot = {"valu":[("multiply_add", load_addr_vec[batch_idx[0]], idx_vec[batch_idx[0]], two_const_vec, node_val_addr_minus_one_vec)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [2,3,8,9,14,15,20,21]])
            # idx 1
            slot = {"valu":[("multiply_add", load_addr_vec[batch_idx[1]], idx_vec[batch_idx[1]], two_const_vec, node_val_addr_minus_one_vec)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [26,27,32,33,38,39,44,45]])
            # idx 2
            slot = {"load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[0]]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [4,5]])
            # idx 3
            slot = {"load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[0]]+1)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [6,7]])
            # idx 4
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+0, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [10]])
            # idx 5
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+0, tmp_vec[0]+1, tmp_vec[0]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [10]])
            # idx 6
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+1, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [10]])
            # idx 7
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+1, tmp_vec[1]+1, tmp_vec[1]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [10]])
            # idx 8
            slot = { "load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[0]]+2)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [10,11]])
            # idx 9
            slot = { "load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[0]]+3)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [12,13]])
            # idx 10
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+2, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [16]])
            # idx 11
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+2, tmp_vec[0]+1, tmp_vec[0]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [16]])
            # idx 12
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+3, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [16]])
            # idx 13
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+3, tmp_vec[1]+1, tmp_vec[1]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [16]])
            # idx 14
            slot = { "load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[0]]+4)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [16,17]])
            # idx 15
            slot = { "load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[0]]+5)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [18,19]])
            # idx 16
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+4, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [22]])
            # idx 17
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+4, tmp_vec[0]+1, tmp_vec[0]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [22]])
            # idx 18
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+5, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [22]])
            # idx 19
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+5, tmp_vec[1]+1, tmp_vec[1]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [22]])
            # idx 20
            slot = {"load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[0]]+6)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [22,23]])
            # idx 21
            slot = {"load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[0]]+7)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [24,25]])
            # idx 22
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+6, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [28]])
            # idx 23
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+6, tmp_vec[0]+1, tmp_vec[0]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [28]])
            # idx 24
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[0]]+7, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [28]])
            # idx 25
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[0]]+7, tmp_vec[1]+1, tmp_vec[1]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [28]])
            # idx 26
            slot = { "load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[1]]+0)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [28,29]])
            # idx 27
            slot = { "load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[1]]+1)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [30,31]])
            # idx 28
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+0, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [34]])
            # idx 29
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+0, tmp_vec[0]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [34]])
            # idx 30
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+1, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [34]])
            # idx 31
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+1, tmp_vec[1]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [34]])
            # idx 32
            slot = { "load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[1]]+2)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [34,35]])
            # idx 33
            slot = { "load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[1]]+3)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [36,37]])
            # idx 34
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+2, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [40]])
            # idx 35
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+2, tmp_vec[0]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [40]])
            # idx 36
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+3, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [40]])
            # idx 37
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+3, tmp_vec[1]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [40]])
            # idx 38
            slot = { "load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[1]]+4)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [40,41]])
            # idx 39
            slot = { "load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[1]]+5)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [42,43]])
            # idx 40
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+4, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [46]])
            # idx 41
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+4, tmp_vec[0]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [46]])
            # idx 42
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+5, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [46]])
            # idx 43
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+5, tmp_vec[1]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [46]])
            # idx 44
            slot = { "load":[("vload", tmp_vec[0], load_addr_vec[batch_idx[1]]+6)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [46,47]])
            # idx 45
            slot = { "load":[("vload", tmp_vec[1], load_addr_vec[batch_idx[1]]+7)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, -1, [48,49]])
            # idx 46
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+6, tmp_vec[0]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, final_required_idx, []])
            # idx 47
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+6, tmp_vec[0]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, final_required_idx, []])
            # idx 48
            slot = { "alu":[("+", next_node_val_vec[0][batch_idx[1]]+7, tmp_vec[1]+0, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, final_required_idx, []])
            # idx 49
            slot = { "alu":[("-", next_node_val_vec[1][batch_idx[1]]+7, tmp_vec[1]+1, zero_const)]}
            load_body.append( [ slot, mod2_ready_vec[2]+1, final_required_idx, []])

        return load_body

    def build_two_instr_full_cycle( self, rounds, height, batch_idx,
                                    value_vec, idx_vec, hash_val1_const_vec, hash_val3_const_vec,
                                    tmp1_vec, tmp2_vec, tmp_load_vec, tmp_vec,
                                    mod2_level_vec, two_const_vec, zero_const,
                                    node_val_vec, node_val_preload_vec, next_node_val_vec,
                                    load_addr_vec, node_val_addr_minus_one_vec,
                                    load_body, start_idx):
        # body is a list of dict. it contains the main instrs for two vector of values of full cycle
        body = []
        # load_body is a list of data structure for each round
        # the data structue is basically a dependency graph which records dependency of each slot and their earliest/latest required instr line numbers
        idx_cnt = start_idx
        for round in range(rounds):
            level = round%(height+1)

            if level == 0:
                # value is preprocessed as value = value ^ node_value[0]
                instr = self.init_instr()
                # value = ( value + hash_val1[0] ) + ( value << 12 ) = hash_val3[0] * value + hash_val1[0]
                instr["valu"].append(("multiply_add", value_vec[batch_idx[0]], hash_val3_const_vec[0], value_vec[batch_idx[0]], hash_val1_const_vec[0]))
                instr["valu"].append(("multiply_add", value_vec[batch_idx[1]], hash_val3_const_vec[0], value_vec[batch_idx[1]], hash_val1_const_vec[0]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value ^ hash_val1[1]
                instr["valu"].append(("^", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val1_const_vec[1]))
                instr["valu"].append(("^", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val1_const_vec[1]))
                # tmp2 = value >> hash_val3[1]
                instr["valu"].append((">>", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[1]))
                instr["valu"].append((">>", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[1]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value * hash_val3[2] + hash_val1[2]
                instr["valu"].append(("multiply_add", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[2], hash_val1_const_vec[2]))
                instr["valu"].append(("multiply_add", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[2], hash_val1_const_vec[2]))
                # tmp2 = value * hash_val3[3] + hash_val1[3]
                instr["valu"].append(("multiply_add", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[3], hash_val1_const_vec[3]))
                instr["valu"].append(("multiply_add", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[3], hash_val1_const_vec[3]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = value * hash_val3[4] + hash_val1[4]
                instr["valu"].append(("multiply_add", value_vec[batch_idx[0]], hash_val3_const_vec[4], value_vec[batch_idx[0]], hash_val1_const_vec[4]))
                instr["valu"].append(("multiply_add", value_vec[batch_idx[1]], hash_val3_const_vec[4], value_vec[batch_idx[1]], hash_val1_const_vec[4]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value ^ hash_val1[5]
                instr["valu"].append(("^", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val1_const_vec[5]))
                instr["valu"].append(("^", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val1_const_vec[5]))
                # tmp2 = value >> hash_val3[5]
                instr["valu"].append((">>", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[5]))
                instr["valu"].append((">>", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[5]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # mod2 = value %2
                instr["valu"].append(("%", mod2_level_vec[0][batch_idx[0]], value_vec[batch_idx[0]], two_const_vec))
                instr["valu"].append(("%", mod2_level_vec[0][batch_idx[1]], value_vec[batch_idx[1]], two_const_vec))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # node_val = mod2 * (node_value[2] - node_value[1]) * node_value[1]
                instr["valu"].append(("multiply_add", node_val_vec[batch_idx[0]], mod2_level_vec[0][batch_idx[0]], node_val_preload_vec[2], node_val_preload_vec[1]))
                instr["valu"].append(("multiply_add", node_val_vec[batch_idx[1]], mod2_level_vec[0][batch_idx[1]], node_val_preload_vec[2], node_val_preload_vec[1]))
                # idx = 2 + mod2
                instr["valu"].append(("+", idx_vec[batch_idx[0]], two_const_vec, mod2_level_vec[0][batch_idx[0]]))
                instr["valu"].append(("+", idx_vec[batch_idx[1]], two_const_vec, mod2_level_vec[0][batch_idx[1]]))
                self.append_instr(body, instr)
                # 10 instrs
                idx_cnt += 10
                mod2_ready_vec = [idx_cnt-2]
                load_body.append( self.generate_load_instrs(rounds, height, batch_idx, round, level, next_node_val_vec, mod2_level_vec, node_val_preload_vec, tmp_load_vec, load_addr_vec, tmp_vec, idx_vec, node_val_addr_minus_one_vec, two_const_vec, zero_const, mod2_ready_vec, idx_cnt-1))
            # last round or last level will early return
            elif (round == rounds - 1) or (level == height):
                # value = value ^ node_value[idx]
                instr = self.init_instr()
                instr["valu"].append(("^", value_vec[batch_idx[0]], value_vec[batch_idx[0]], node_val_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], value_vec[batch_idx[1]], node_val_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = ( value + hash_val1[0] ) + ( value << 12 ) = hash_val3[0] * value + hash_val1[0]
                instr["valu"].append(("multiply_add", value_vec[batch_idx[0]], hash_val3_const_vec[0], value_vec[batch_idx[0]], hash_val1_const_vec[0]))
                instr["valu"].append(("multiply_add", value_vec[batch_idx[1]], hash_val3_const_vec[0], value_vec[batch_idx[1]], hash_val1_const_vec[0]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value ^ hash_val1[1]
                instr["valu"].append(("^", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val1_const_vec[1]))
                instr["valu"].append(("^", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val1_const_vec[1]))
                # tmp2 = value >> hash_val3[1]
                instr["valu"].append((">>", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[1]))
                instr["valu"].append((">>", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[1]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value * hash_val3[2] + hash_val1[2]
                instr["valu"].append(("multiply_add", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[2], hash_val1_const_vec[2]))
                instr["valu"].append(("multiply_add", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[2], hash_val1_const_vec[2]))
                # tmp2 = value * hash_val3[3] + hash_val1[3]
                instr["valu"].append(("multiply_add", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[3], hash_val1_const_vec[3]))
                instr["valu"].append(("multiply_add", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[3], hash_val1_const_vec[3]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = value * hash_val3[4] + hash_val1[4]
                instr["valu"].append(("multiply_add", value_vec[batch_idx[0]], hash_val3_const_vec[4], value_vec[batch_idx[0]], hash_val1_const_vec[4]))
                instr["valu"].append(("multiply_add", value_vec[batch_idx[1]], hash_val3_const_vec[4], value_vec[batch_idx[1]], hash_val1_const_vec[4]))
                if level == height:
                    # preprocess value ^ node_val[0]
                    instr["valu"].append(("^", tmp1_vec[batch_idx[0]], node_val_preload_vec[0], hash_val1_const_vec[5]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value ^ hash_val1[5]
                if level == height:
                    instr["valu"].append(("^", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]]))
                    instr["valu"].append(("^", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], tmp1_vec[batch_idx[0]]))
                else:
                    instr["valu"].append(("^", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val1_const_vec[5]))
                    instr["valu"].append(("^", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val1_const_vec[5]))
                # tmp2 = value >> hash_val3[5]
                instr["valu"].append((">>", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[5]))
                instr["valu"].append((">>", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[5]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                # 9 instrs
                idx_cnt += 9
                load_body.append( self.generate_load_instrs(rounds, height, batch_idx, round, level, next_node_val_vec, mod2_level_vec, node_val_preload_vec, tmp_load_vec, load_addr_vec, tmp_vec, idx_vec, node_val_addr_minus_one_vec, two_const_vec, zero_const, mod2_ready_vec, idx_cnt-1))
            else:
                # value = value ^ node_value[idx]
                instr = self.init_instr()
                instr["valu"].append(("^", value_vec[batch_idx[0]], value_vec[batch_idx[0]], node_val_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], value_vec[batch_idx[1]], node_val_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = ( value + hash_val1[0] ) + ( value << 12 ) = hash_val3[0] * value + hash_val1[0]
                instr["valu"].append(("multiply_add", value_vec[batch_idx[0]], hash_val3_const_vec[0], value_vec[batch_idx[0]], hash_val1_const_vec[0]))
                instr["valu"].append(("multiply_add", value_vec[batch_idx[1]], hash_val3_const_vec[0], value_vec[batch_idx[1]], hash_val1_const_vec[0]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value ^ hash_val1[1]
                instr["valu"].append(("^", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val1_const_vec[1]))
                instr["valu"].append(("^", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val1_const_vec[1]))
                # tmp2 = value >> hash_val3[1]
                instr["valu"].append((">>", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[1]))
                instr["valu"].append((">>", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[1]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value * hash_val3[2] + hash_val1[2]
                instr["valu"].append(("multiply_add", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[2], hash_val1_const_vec[2]))
                instr["valu"].append(("multiply_add", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[2], hash_val1_const_vec[2]))
                # tmp2 = value * hash_val3[3] + hash_val1[3]
                instr["valu"].append(("multiply_add", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[3], hash_val1_const_vec[3]))
                instr["valu"].append(("multiply_add", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[3], hash_val1_const_vec[3]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = value * hash_val3[4] + hash_val1[4]
                instr["valu"].append(("multiply_add", value_vec[batch_idx[0]], hash_val3_const_vec[4], value_vec[batch_idx[0]], hash_val1_const_vec[4]))
                instr["valu"].append(("multiply_add", value_vec[batch_idx[1]], hash_val3_const_vec[4], value_vec[batch_idx[1]], hash_val1_const_vec[4]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # tmp1 = value ^ hash_val1[5]
                instr["valu"].append(("^", tmp1_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val1_const_vec[5]))
                instr["valu"].append(("^", tmp1_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val1_const_vec[5]))
                # tmp2 = value >> hash_val3[5]
                instr["valu"].append((">>", tmp2_vec[batch_idx[0]], value_vec[batch_idx[0]], hash_val3_const_vec[5]))
                instr["valu"].append((">>", tmp2_vec[batch_idx[1]], value_vec[batch_idx[1]], hash_val3_const_vec[5]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # value = tmp1 ^ tmp2
                instr["valu"].append(("^", value_vec[batch_idx[0]], tmp1_vec[batch_idx[0]], tmp2_vec[batch_idx[0]]))
                instr["valu"].append(("^", value_vec[batch_idx[1]], tmp1_vec[batch_idx[1]], tmp2_vec[batch_idx[1]]))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # mod2 = value %2
                instr["valu"].append(("%", mod2_level_vec[level%4][batch_idx[0]], value_vec[batch_idx[0]], two_const_vec))
                instr["valu"].append(("%", mod2_level_vec[level%4][batch_idx[1]], value_vec[batch_idx[1]], two_const_vec))
                self.append_instr(body, instr)

                instr = self.init_instr()
                # node_val = mod2 * (node_value[2] - node_value[1]) * node_value[1]
                instr["valu"].append(("multiply_add", node_val_vec[batch_idx[0]], mod2_level_vec[level%4][batch_idx[0]], next_node_val_vec[1][batch_idx[0]], next_node_val_vec[0][batch_idx[0]]))
                instr["flow"].append(("vselect", node_val_vec[batch_idx[1]], mod2_level_vec[level%4][batch_idx[1]], next_node_val_vec[1][batch_idx[1]], next_node_val_vec[0][batch_idx[1]]))
                # idx = 2 * idx + mod2
                instr["valu"].append(("multiply_add", idx_vec[batch_idx[0]], idx_vec[batch_idx[0]], two_const_vec, mod2_level_vec[level%4][batch_idx[0]]))
                instr["valu"].append(("multiply_add", idx_vec[batch_idx[1]], idx_vec[batch_idx[1]], two_const_vec, mod2_level_vec[level%4][batch_idx[1]]))
                self.append_instr(body, instr)
                # 11 instrs
                idx_cnt += 11
                load_body.append( self.generate_load_instrs(rounds, height, batch_idx, round, level, next_node_val_vec, mod2_level_vec, node_val_preload_vec, tmp_load_vec, load_addr_vec, tmp_vec, idx_vec, node_val_addr_minus_one_vec, two_const_vec, zero_const, mod2_ready_vec, idx_cnt-1 ))
                if len(mod2_ready_vec) >= 3:
                    mod2_ready_vec.pop(0)
                mod2_ready_vec.append(idx_cnt-2)
        return body

    def build_kernel(
        self, forest_height: int, n_nodes: int, batch_size: int, rounds: int
    ):
        """
        Like reference_kernel2 but building actual instructions.
        Scalar implementation using only scalar ALU and load/store.
        """
        batch_load_size = 4
        batch_stride_imm = batch_load_size * VLEN
        tmp1_vec = []
        tmp2_vec = []
        tmp_vec = []
        for i in range(0,2):
            tmp_vec.append(self.alloc_scratch(f"tmp{i}_vec",batch_stride_imm))
        for i in range(batch_load_size):
            tmp1_vec.append(tmp_vec[0]+i*VLEN)
            tmp2_vec.append(tmp_vec[1]+i*VLEN)
        tmp_vec = []
        for i in range(0,2):
            tmp_vec.append(self.alloc_scratch(f"tmp{i}",VLEN))
        tmp_load_vec = []
        for i in range(12):
            tmp_load = []
            for j in range(batch_load_size):
                tmp_load.append(self.alloc_scratch(f"tmp_load_{i}_{j}", VLEN))
            tmp_load_vec.append(tmp_load)
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

        # Pause instructions are matched up with yield statements in the reference
        # kernel to let you debug at intermediate steps. The testing harness in this
        # file requires these match up to the reference kernel's yields, but the
        # submission harness ignores them.
        self.add("flow", ("pause",))
        # Any debug engine instruction is ignored by the submission simulator
        self.add("debug", ("comment", "Starting loop"))

        # allocate cache
        tmp_idx = self.alloc_scratch("tmp_idx",batch_stride_imm)
        tmp_val = self.alloc_scratch("tmp_val",batch_size)
        node_val = self.alloc_scratch("node_val",batch_stride_imm)
        # let index be 1-2047
        tmp_idx_vec = []
        tmp_val_vec = []
        node_val_vec = []
        next_node_val_1_vec = []
        next_node_val_2_vec = []
        next_node_val_1 = self.alloc_scratch("next_node_val1",batch_stride_imm)
        next_node_val_2 = self.alloc_scratch("next_node_val2",batch_stride_imm)
        store_load_val_addr = self.alloc_scratch("store_load_val_addr",batch_load_size)
        store_load_val_addr_vec = []
        tmp_load_val_addr = self.alloc_scratch("tmp_load_val_addr",batch_load_size)
        tmp_load_val_addr_vec = []
        for i in range(batch_load_size) :
            tmp_idx_vec.append(tmp_idx+i * VLEN)
            tmp_val_vec.append(tmp_val+i * VLEN)
            node_val_vec.append(node_val+i * VLEN)
            next_node_val_1_vec.append( next_node_val_1+i * VLEN)
            next_node_val_2_vec.append( next_node_val_2+i * VLEN)
            store_load_val_addr_vec.append(store_load_val_addr+i)
            tmp_load_val_addr_vec.append(tmp_load_val_addr+i)
        next_addr = self.alloc_scratch("next_addr", batch_stride_imm)
        load_addr_vec = []
        for i in range(batch_load_size) :
            load_addr_vec.append(next_addr + i * VLEN )
        next_node_val = []
        next_node_val.append( next_node_val_1_vec )
        next_node_val.append( next_node_val_2_vec )

        # vec const value
        node_val_addr.append(self.scratch["forest_values_p"])

        preload_size = 32
        for i in range(1,preload_size//VLEN):
            node_val_addr.append(self.alloc_scratch(f"node_val_addr_VLEN_{i}"))
        valMod2 = self.alloc_scratch("valMod2",4*batch_stride_imm)
        valMod2_vec_level = []
        for j in range(4):
            valMod2_vec = []
            for i in range(batch_load_size):
                valMod2_vec.append(valMod2+ i*VLEN + j*batch_stride_imm)
            valMod2_vec_level.append(valMod2_vec)
        const_node_val_vec = self.alloc_scratch("const_node_val_vec",preload_size)
        node_val_preload_vec = []
        for i in range(preload_size):
            node_val_preload_vec.append(self.alloc_scratch(f"node_val_preload_vec_{i}",VLEN))

        node_val_addr_minus_one_vec = self.alloc_scratch("node_val_addr_minus_one_vec",VLEN)

        # Scalar scratch registers
        # hash const and multiplier
        two_const_vec = self.alloc_scratch("two_const_vec",VLEN)
        zero_const_vec = self.alloc_scratch("zero_const_vec",VLEN)
        instr = self.scratch_two_const(0,VLEN)
        zero_const = self.scratch_const(0)
        self.append_instr( body, instr )

        hash_val3_const = []
        hash_val1_const = []

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        instr["load"].append(("vload",self.scratch["rounds"],zero_const))
        addr = self.alloc_scratch()
        self.const_map[9] = addr
        instr["load"].append(("const",addr,9))
        addr = self.alloc_scratch()
        self.const_map[0x7ED55D16] = addr
        instr["flow"].append(("add_imm", addr, zero_const, 0x7ED55D16))
        hash_val1_const.append(addr)
        self.append_instr( body, instr )

        instr = self.scratch_two_const(2*VLEN,3*VLEN)
        addr = self.alloc_scratch()
        self.const_map[0xC761C23C] = addr
        instr["flow"].append(("add_imm", addr, zero_const, 0xC761C23C))
        hash_val1_const.append(addr)
        instr["valu"].append(("vbroadcast", zero_const_vec, zero_const ))
        instr["alu"].append(("+",node_val_addr[1],node_val_addr[0],self.scratch_const(VLEN)))
        self.append_instr( body, instr )

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        # preload node_val[0:7] into const_node_val_vec
        instr["load"].append(("vload",const_node_val_vec,node_val_addr[0]))
        instr["load"].append(("vload",const_node_val_vec+VLEN,node_val_addr[1]))
        one_const = self.alloc_scratch()
        self.const_map[1] = one_const
        instr["flow"].append(("add_imm", one_const, zero_const, 1))
        instr["alu"].append(("+", store_load_val_addr_vec[0], inp_val_addr, zero_const))
        instr["alu"].append(("+", store_load_val_addr_vec[1], inp_val_addr, self.scratch_const(VLEN)))
        instr["alu"].append(("+", store_load_val_addr_vec[2], inp_val_addr, self.scratch_const(2*VLEN)))
        instr["alu"].append(("+", store_load_val_addr_vec[3], inp_val_addr, self.scratch_const(3*VLEN)))
        instr["alu"].append(("+",node_val_addr[2],node_val_addr[0],self.scratch_const(2*VLEN)))
        instr["alu"].append(("+",node_val_addr[3],node_val_addr[0],self.scratch_const(3*VLEN)))
        self.append_instr( body, instr )

        instr = self.scratch_two_const(4097,19)
        hash_val3_const.append(self.scratch_const(4097))
        hash_val3_const.append(self.scratch_const(19))
        batch_stride = self.alloc_scratch()
        self.const_map[batch_stride_imm] = batch_stride
        instr["flow"].append(("add_imm", batch_stride, zero_const, batch_stride_imm))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[0], const_node_val_vec+0 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[1], const_node_val_vec+1 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[3], const_node_val_vec+3 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[4], const_node_val_vec+4 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[6], const_node_val_vec+6 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[7], const_node_val_vec+7 ))
        for os in range(0,4):
            instr["alu"].append(("-",node_val_preload_vec[2]+os,const_node_val_vec+2,const_node_val_vec+1))
            instr["alu"].append(("-",node_val_preload_vec[5]+os,const_node_val_vec+5,const_node_val_vec+3))
            instr["alu"].append(("-",node_val_preload_vec[14]+os,const_node_val_vec+14,zero_const))
        self.append_instr( body, instr )

        hash_val3_const_vec = []
        hash_val1_const_vec = []
        # val3 of op4 and op5 are same( both 9)
        for i in range(6):
             hash_val3_const_vec.append(self.alloc_scratch(f"hash_val3_const_{i}_vec",VLEN))
             hash_val1_const_vec.append(self.alloc_scratch(f"hash_val1_const_{i}_vec",VLEN))

        # 33, 33<<9
        instr = self.scratch_two_const(33,16896)
        hash_val3_const.append(self.scratch_const(33))
        hash_val3_const.append(self.scratch_const(16896))
        hash_val3_const.append(self.scratch_const(9))
        hash_val3_const.append(self.scratch_const(16))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[8], const_node_val_vec+8 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[9], const_node_val_vec+9 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[10], const_node_val_vec+10 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[11], const_node_val_vec+11 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[12], const_node_val_vec+12 ))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[13], const_node_val_vec+13 ))
        for os in range(batch_load_size):
            instr["alu"].append(("+", tmp_load_val_addr_vec[os], store_load_val_addr_vec[os], batch_stride))
        # 0x165667B1+0xD3A2646C, 0x165667B1<<9
        addr = self.alloc_scratch()
        self.const_map[0xE9F8CC1D] = addr
        instr["flow"].append(("add_imm", addr, zero_const, 0xE9F8CC1D))
        hash_val1_const.append(addr)
        self.append_instr( body, instr )

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        # preload tmp_val = values[0:7]
        instr["load"].append(("vload", tmp_val_vec[0], store_load_val_addr_vec[0]))
        # preload tmp_val = values[16:23]
        instr["load"].append(("vload", tmp_val_vec[1], store_load_val_addr_vec[1]))
        for os in range(0,6):
            instr["valu"].append(("vbroadcast", hash_val3_const_vec[os], hash_val3_const[os] ))
        for os in range(4,8):
            instr["alu"].append(("-",node_val_preload_vec[2]+os,const_node_val_vec+2,const_node_val_vec+1))
            instr["alu"].append(("-",node_val_preload_vec[5]+os,const_node_val_vec+5,const_node_val_vec+3))
            instr["alu"].append(("-",node_val_preload_vec[14]+os,const_node_val_vec+14,zero_const))
        # 0x165667B1+0xD3A2646C, 0x165667B1<<9
        addr = self.alloc_scratch()
        self.const_map[0xACCF6200] = addr
        instr["flow"].append(("add_imm", addr, zero_const, 0xACCF6200))
        hash_val1_const.append(addr)
        self.append_instr( body, instr )

        instr = self.scratch_two_const(0xFD7046C5,0xB55A4F09)
        hash_val1_const.append(self.scratch_const(0xFD7046C5))
        hash_val1_const.append(self.scratch_const(0xB55A4F09))
        # pre calculate tmp_val = tmp_val ^ node_val[0]
        instr["valu"].append(("^", tmp_val_vec[0], tmp_val_vec[0], node_val_preload_vec[0]))
        instr["valu"].append(("^", tmp_val_vec[1], tmp_val_vec[1], node_val_preload_vec[0]))
        for os in range(0,8):
            instr["alu"].append(("-", node_val_addr_minus_one_vec+os, forest_val_addr, one_const ))
        for os in range(0,2):
            instr["valu"].append(("vbroadcast", hash_val1_const_vec[os], hash_val1_const[os]))
        instr["valu"].append(("vbroadcast", node_val_preload_vec[15], const_node_val_vec+15 ))
        two_const = self.alloc_scratch()
        self.const_map[2] = two_const
        instr["flow"].append(("add_imm", two_const, zero_const, 2))
        self.append_instr( body, instr )

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        instr["load"].append(("vload",const_node_val_vec+2*VLEN,node_val_addr[2]))
        instr["load"].append(("vload",const_node_val_vec+3*VLEN,node_val_addr[3]))
        for os in range(2,6):
            instr["valu"].append(("vbroadcast", hash_val1_const_vec[os], hash_val1_const[os]))
        instr["valu"].append(("vbroadcast", two_const_vec, two_const ))
        self.append_instr( body, instr )

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        # preload tmp_val = values[8:15]
        instr["load"].append(("vload", tmp_val_vec[2], store_load_val_addr_vec[2]))
        # preload tmp_val = values[24:31]
        instr["load"].append(("vload", tmp_val_vec[3], store_load_val_addr_vec[3]))
        for os in range(16,22):
            instr["valu"].append(("vbroadcast", node_val_preload_vec[os], const_node_val_vec+os ))
        for os in range(0,8):
            instr["alu"].append(("-", node_val_preload_vec[30]+os, const_node_val_vec+30, const_node_val_vec+22))
        for os in range(0,4):
            instr["alu"].append(("-", node_val_preload_vec[29]+os, const_node_val_vec+29, const_node_val_vec+21))
        self.append_instr( body, instr )

        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        for os in range(22,28):
            instr["valu"].append(("vbroadcast", node_val_preload_vec[os], const_node_val_vec+os ))
        for os in range(4,8):
            instr["alu"].append(("-", node_val_preload_vec[29]+os, const_node_val_vec+29, const_node_val_vec+21))
        for os in range(0,8):
            instr["alu"].append(("-", node_val_preload_vec[28]+os, const_node_val_vec+28, const_node_val_vec+20))
        self.append_instr( body, instr )

        # pre calculate tmp_val = tmp_val ^ node_val[0]
        instr = {"alu":[],"valu":[],"flow":[],"load":[],"store":[]}
        instr["valu"].append(("^", tmp_val_vec[2], tmp_val_vec[2], node_val_preload_vec[0]))
        instr["valu"].append(("^", tmp_val_vec[3], tmp_val_vec[3], node_val_preload_vec[0]))
        for os in range(26,28):
            instr["valu"].append(("-", node_val_preload_vec[os], node_val_preload_vec[os], node_val_preload_vec[os-8] ))
        self.append_instr( body, instr )

        print("initialization instructions length is ", len(body))
        print("n_nodes=", n_nodes)
        print("SCRATCH_SIZE=", SCRATCH_SIZE, " used size=", self.scratch_ptr)

        # notice initial index of all elements in batch are 0. It means each round index will be in the same level of the tree
        # for round #1, broadcast const zero to all index
        # for round #2, select between const one and const two based on val%2
        # 256 / 8 / 4 = 8
        batch_one_body = []
        batch_one_load_body = []
        batch_idx = [0,1]
        for i in range(0,batch_size, batch_stride_imm):
            # idx = 0
            # val = mem[inp_values_p + i]
            # node_val = node_val[0]
            # 16
            # unroll
            start_idx = len(batch_one_body)
            batch_one_body.extend(self.build_two_instr_full_cycle( rounds, forest_height, batch_idx,
                                                                   tmp_val_vec, tmp_idx_vec, hash_val1_const_vec, hash_val3_const_vec,
                                                                   tmp1_vec, tmp2_vec, tmp_load_vec, tmp_vec,
                                                                   valMod2_vec_level, two_const_vec, zero_const,
                                                                   node_val_vec, node_val_preload_vec, next_node_val,
                                                                   load_addr_vec, node_val_addr_minus_one_vec,
                                                                   batch_one_load_body, start_idx))
            instr = self.init_instr()
            instr["store"].append(("vstore", store_load_val_addr_vec[0], tmp_val_vec[0]))
            instr["store"].append(("vstore", store_load_val_addr_vec[1], tmp_val_vec[1]))
            if i != batch_size - batch_stride_imm :
                instr["valu"].append(("+", tmp_val_vec[0], tmp_val_vec[0]+i+batch_stride_imm,zero_const_vec))
                instr["valu"].append(("+", tmp_val_vec[1], tmp_val_vec[1]+i+batch_stride_imm,zero_const_vec))
                instr["alu"].append(("+", store_load_val_addr_vec[0], store_load_val_addr_vec[0], batch_stride))
                instr["alu"].append(("+", store_load_val_addr_vec[1], store_load_val_addr_vec[1], batch_stride))
            batch_one_body.append(instr)
            # padding instr
            instr = self.init_instr()
            batch_one_body.append(instr)
            # padding instr
            instr = self.init_instr()
            batch_one_body.append(instr)

        batch_two_body = []
        batch_two_load_body = []
        batch_idx = [2,3]
        offset = 78
        for i in range(0,batch_size, batch_stride_imm):
            # idx = 0
            # val = mem[inp_values_p + i]
            # node_val = node_val[0]
            # 16
            # unroll
            start_idx = len(batch_two_body)+offset
            batch_two_body.extend(self.build_two_instr_full_cycle( rounds, forest_height, batch_idx,
                                                                   tmp_val_vec, tmp_idx_vec, hash_val1_const_vec, hash_val3_const_vec,
                                                                   tmp1_vec, tmp2_vec, tmp_load_vec, tmp_vec,
                                                                   valMod2_vec_level, two_const_vec, zero_const,
                                                                   node_val_vec, node_val_preload_vec, next_node_val,
                                                                   load_addr_vec, node_val_addr_minus_one_vec,
                                                                   batch_two_load_body, start_idx))
            instr = self.init_instr()
            instr["store"].append(("vstore", store_load_val_addr_vec[2], tmp_val_vec[2]))
            instr["store"].append(("vstore", store_load_val_addr_vec[3], tmp_val_vec[3]))
            if i != batch_size - batch_stride_imm :
                instr["valu"].append(("+", tmp_val_vec[2], tmp_val_vec[2]+i+batch_stride_imm, zero_const_vec))
                instr["valu"].append(("+", tmp_val_vec[3], tmp_val_vec[3]+i+batch_stride_imm, zero_const_vec))
                instr["alu"].append(("+", store_load_val_addr_vec[2], store_load_val_addr_vec[2], batch_stride))
                instr["alu"].append(("+", store_load_val_addr_vec[3], store_load_val_addr_vec[3], batch_stride))
            batch_two_body.append(instr)
            # padding instr
            instr = self.init_instr()
            batch_two_body.append(instr)
            # padding instr
            instr = self.init_instr()
            batch_two_body.append(instr)
        
        # create instrs to load batch value and merge them at the begining of batch_one_body when batch_two_body has not started yet
        load_batch_body = []
        for i in range(batch_stride_imm,batch_size,batch_stride_imm):
            instr = self.init_instr()
            if i != batch_stride_imm:
                instr["alu"].append(("+", tmp_load_val_addr_vec[2], tmp_load_val_addr_vec[2], batch_stride))
                instr["alu"].append(("+", tmp_load_val_addr_vec[3], tmp_load_val_addr_vec[3], batch_stride))
                instr["valu"].append(("^", tmp_val_vec[2]+i-batch_stride_imm, tmp_val_vec[2]+i-batch_stride_imm, node_val_preload_vec[0]))
                instr["valu"].append(("^", tmp_val_vec[3]+i-batch_stride_imm, tmp_val_vec[3]+i-batch_stride_imm, node_val_preload_vec[0]))
            instr["load"].append(("vload", tmp_val_vec[0]+i, tmp_load_val_addr_vec[0]))
            instr["load"].append(("vload", tmp_val_vec[1]+i, tmp_load_val_addr_vec[1]))
            load_batch_body.append(instr)
            instr = self.init_instr()
            if i != batch_size - batch_stride_imm:
                instr["alu"].append(("+", tmp_load_val_addr_vec[0], tmp_load_val_addr_vec[0], batch_stride))
                instr["alu"].append(("+", tmp_load_val_addr_vec[1], tmp_load_val_addr_vec[1], batch_stride))
            instr["valu"].append(("^", tmp_val_vec[0]+i, tmp_val_vec[0]+i, node_val_preload_vec[0]))
            instr["valu"].append(("^", tmp_val_vec[1]+i, tmp_val_vec[1]+i, node_val_preload_vec[0]))
            instr["load"].append(("vload", tmp_val_vec[2]+i, tmp_load_val_addr_vec[2]))
            instr["load"].append(("vload", tmp_val_vec[3]+i, tmp_load_val_addr_vec[3]))
            load_batch_body.append(instr)
        instr = self.init_instr()
        instr["valu"].append(("^", tmp_val_vec[2]+batch_size-batch_stride_imm, tmp_val_vec[2]+batch_size-batch_stride_imm, node_val_preload_vec[0]))
        instr["valu"].append(("^", tmp_val_vec[3]+batch_size-batch_stride_imm, tmp_val_vec[3]+batch_size-batch_stride_imm, node_val_preload_vec[0]))
        load_batch_body.append(instr)

        self.merge_batch( batch_one_body, load_batch_body, 0, zero_const)

        assert len(batch_one_body) == len(batch_two_body)
        self.merge_batch( batch_one_body, batch_two_body, offset, zero_const, True )
        print("main body instructions length is ", len(batch_one_body), " offset is ", offset, " load one len is ", len(batch_one_load_body), " load two len is ", len(batch_two_load_body) )

        #print("Before merge load")
        #for idx in range(22,32):
        #    print("#",idx, " instr: ", batch_one_body[idx])
        # round 3-9 is more critical since there is no margin(available instrs and required instrs are both 11)
        critical_load_body = [[] for _ in range(len(batch_one_load_body))]
        for idx,round_body in enumerate(batch_one_load_body):
            if idx%16 > 2 and idx%16 < 10:
                critical_load_body[idx] = round_body
        self.merge_load( batch_one_body, critical_load_body, zero_const, False )
        for idx,round_body in enumerate(batch_two_load_body):
            if idx%16 > 2 and idx%16 < 10:
                critical_load_body[idx] = round_body
        self.merge_load( batch_one_body, critical_load_body, zero_const, False )

        remain_load_body = [[] for _ in range(len(batch_one_load_body))]
        for idx,round_body in enumerate(batch_one_load_body):
            if idx%16 <= 2 or idx%16 > 9:
                remain_load_body[idx] = round_body
        
        self.merge_load( batch_one_body, remain_load_body, zero_const, False )
        for idx,round_body in enumerate(batch_two_load_body):
            if idx%16 <= 2 or idx%16 > 9:
                remain_load_body[idx] = round_body
        self.merge_load( batch_one_body, remain_load_body, zero_const, False )
        # debug
        if False:
            for idx in range(150,161):
                remain_slots = {"alu":0,"valu":0,"flow":0,"load":0,"store":0}
                for ops in remain_slots:
                    remain_slots[ops] = SLOT_LIMITS[ops] - len(batch_one_body[idx][ops])
                print("#", idx, "remain:", remain_slots)
                for ops in remain_slots:
                    print(ops,":", batch_one_body[idx][ops])

        body.extend( batch_one_body )
        # debug
        if False:
            for idx in range(151,182):
                remain_slots = {"alu":0,"valu":0,"flow":0,"load":0,"store":0}
                for ops in remain_slots:
                    remain_slots[ops] = SLOT_LIMITS[ops] - len(body[idx][ops])
                print("#", idx, "remain:", remain_slots)
                for ops in remain_slots:
                    print(ops,":", body[idx][ops])

        #for i in range(16):
        #    print( "#", i, " load:", batch_one_load_body[i])

        #for i in range(16):
        #    print( "#", i, " load:", batch_two_load_body[i])

        print("total instructions length is ", len(body))

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
