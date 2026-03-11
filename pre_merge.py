

# level 2
#input: volMod2_vec_level[0-1][0-3]
#       node_val_preload_vec[3-6]
                    # preprocess node_val picking for level 1
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[0]+1][0],valMod2_vec_level[0][0],tmp3,node_val_preload_vec[4]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[0]+ 0][0], valMod2_vec_level[0][0], node_val_preload_vec[5], node_val_preload_vec[3]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[0]+1][0]+os,merge_node_vec[merge_vec_idx[0]+1][0]+os,merge_node_vec[merge_vec_idx[0]+0][0]+os))
======>>>>>

# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[0]+1][0], merge_node_vec[merge_vec_idx[0]+0][0]))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[0]+1][2],valMod2_vec_level[0][2],tmp3,node_val_preload_vec[4]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[0]+ 0][2], valMod2_vec_level[0][2], node_val_preload_vec[5], node_val_preload_vec[3]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[0]+1][2]+os,merge_node_vec[merge_vec_idx[0]+1][2]+os,merge_node_vec[merge_vec_idx[0]+0][2]+os))
======>>>>>

# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[0]+1][2], merge_node_vec[merge_vec_idx[0]+0][2]))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[0]+1][1],valMod2_vec_level[0][1],tmp3,node_val_preload_vec[4]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[0]+ 0][1], valMod2_vec_level[0][1], node_val_preload_vec[5], node_val_preload_vec[3]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[0]+1][1]+os,merge_node_vec[merge_vec_idx[0]+1][1]+os,merge_node_vec[merge_vec_idx[0]+0][1]+os))
======>>>>>

# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[0]+1][1], merge_node_vec[merge_vec_idx[0]+0][1]))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[0]+1][3],valMod2_vec_level[0][3],tmp3,node_val_preload_vec[4]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[0]+ 0][3], valMod2_vec_level[0][3], node_val_preload_vec[5], node_val_preload_vec[3]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[0]+1][3]+os,merge_node_vec[merge_vec_idx[0]+1][3]+os,merge_node_vec[merge_vec_idx[0]+0][3]+os))
======>>>>>

# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[0]+1][3], merge_node_vec[merge_vec_idx[0]+0][3]))
======================================

# level 3
#input: volMod2_vec_level[0-2][0-3]
#       node_val_preload_vec[7-14]
# after valMod2_vec_level[0][0] available
                    # preprocess node_val picking for level 2
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+2][0],valMod2_vec_level[0][0],tmp4,node_val_preload_vec[9]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 0][0], valMod2_vec_level[0][0], node_val_preload_vec[11], node_val_preload_vec[7]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+2][0]+os,merge_node_vec[merge_vec_idx[1]+2][0]+os,merge_node_vec[merge_vec_idx[1]+0][0]+os))
======>>>>>

======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+3][0],valMod2_vec_level[0][0],tmp5,node_val_preload_vec[10]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 1][0], valMod2_vec_level[0][0], node_val_preload_vec[12], node_val_preload_vec[8]))

                    for os in range(0,8):
======>>>>>
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+3][0]+os,merge_node_vec[merge_vec_idx[1]+3][0]+os,merge_node_vec[merge_vec_idx[1]+1][0]+os))

======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[1]+2][0], merge_node_vec[merge_vec_idx[1]+0][0]))
======>>>>>
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+1][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[1]+3][0], merge_node_vec[merge_vec_idx[1]+1][0]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+1][0]+os,merge_node_vec[merge_vec_idx[1]+1][0]+os,merge_node_vec[merge_vec_idx[1]+0][0]+os))

=========================================================================
# after valMod2_vec_level[2][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[0], valMod2_vec_level[2][0], merge_node_vec[merge_vec_idx[1]+1][0], merge_node_vec[merge_vec_idx[1]+0][0]))

==================================================================================================================================================================
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+2][2],valMod2_vec_level[0][2],tmp4,node_val_preload_vec[9]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 0][2], valMod2_vec_level[0][2], node_val_preload_vec[11], node_val_preload_vec[7]))
======>>>>>

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+2][2]+os,merge_node_vec[merge_vec_idx[1]+2][2]+os,merge_node_vec[merge_vec_idx[1]+0][2]+os))

======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+3][2],valMod2_vec_level[0][2],tmp5,node_val_preload_vec[10]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 1][2], valMod2_vec_level[0][2], node_val_preload_vec[12], node_val_preload_vec[8]))
======>>>>>

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+3][2]+os,merge_node_vec[merge_vec_idx[1]+3][2]+os,merge_node_vec[merge_vec_idx[1]+1][2]+os))

======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[1]+2][2], merge_node_vec[merge_vec_idx[1]+0][2]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+1][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[1]+3][2], merge_node_vec[merge_vec_idx[1]+1][2]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+1][2]+os,merge_node_vec[merge_vec_idx[1]+1][2]+os,merge_node_vec[merge_vec_idx[1]+0][2]+os))

=========================================================================
# after valMod2_vec_level[2][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[2], valMod2_vec_level[2][2], merge_node_vec[merge_vec_idx[1]+1][2], merge_node_vec[merge_vec_idx[1]+0][2]))

==================================================================================================================================================================

# after valMod2_vec_level[0][0] available
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+2][1],valMod2_vec_level[0][1],tmp4,node_val_preload_vec[9]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 0][1], valMod2_vec_level[0][1], node_val_preload_vec[11], node_val_preload_vec[7]))
======>>>>>

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+2][1]+os,merge_node_vec[merge_vec_idx[1]+2][1]+os,merge_node_vec[merge_vec_idx[1]+0][1]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+3][1],valMod2_vec_level[0][1],tmp5,node_val_preload_vec[10]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 1][1], valMod2_vec_level[0][1], node_val_preload_vec[12], node_val_preload_vec[8]))
======>>>>>

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+3][1]+os,merge_node_vec[merge_vec_idx[1]+3][1]+os,merge_node_vec[merge_vec_idx[1]+1][1]+os))
======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[1]+2][1], merge_node_vec[merge_vec_idx[1]+0][1]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+1][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[1]+3][1], merge_node_vec[merge_vec_idx[1]+1][1]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+1][1]+os,merge_node_vec[merge_vec_idx[1]+1][1]+os,merge_node_vec[merge_vec_idx[1]+0][1]+os))
=========================================================================
# after valMod2_vec_level[2][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[1], valMod2_vec_level[2][1], merge_node_vec[merge_vec_idx[1]+1][1], merge_node_vec[merge_vec_idx[1]+0][1]))

======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+2][3],valMod2_vec_level[0][3],tmp4,node_val_preload_vec[9]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 0][3], valMod2_vec_level[0][3], node_val_preload_vec[11], node_val_preload_vec[7]))
======>>>>>

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+2][3]+os,merge_node_vec[merge_vec_idx[1]+2][3]+os,merge_node_vec[merge_vec_idx[1]+0][3]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[1]+3][3],valMod2_vec_level[0][3],tmp5,node_val_preload_vec[10]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[1]+ 1][3], valMod2_vec_level[0][3], node_val_preload_vec[12], node_val_preload_vec[8]))
======>>>>>

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+3][3]+os,merge_node_vec[merge_vec_idx[1]+3][3]+os,merge_node_vec[merge_vec_idx[1]+1][3]+os))

======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+0][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[1]+2][3], merge_node_vec[merge_vec_idx[1]+0][3]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[1]+1][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[1]+3][3], merge_node_vec[merge_vec_idx[1]+1][3]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[1]+1][3]+os,merge_node_vec[merge_vec_idx[1]+1][3]+os,merge_node_vec[merge_vec_idx[1]+0][3]+os))
=========================================================================
# after valMod2_vec_level[2][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[3], valMod2_vec_level[2][3], merge_node_vec[merge_vec_idx[1]+1][3], merge_node_vec[merge_vec_idx[1]+0][3]))
==================================================================================================================================================================

# level 4
#input: volMod2_vec_level[0-3][0-3]
#       node_val_preload_vec[15-30]
                    # preprocess node_val picking for level 3
======>>>>>
=========================================================================
==================================================================================================================================================================
# for 0
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+4][0],valMod2_vec_level[0][0],tmp6,node_val_preload_vec[19]))
======>>>>>
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 0][0], valMod2_vec_level[0][0], node_val_preload_vec[23], node_val_preload_vec[15]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+4][0]+os,merge_node_vec[merge_vec_idx[2]+4][0]+os,merge_node_vec[merge_vec_idx[2]+0][0]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+6][0],valMod2_vec_level[0][0],tmp8,node_val_preload_vec[21]))
======>>>>>
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 2][0], valMod2_vec_level[0][0], node_val_preload_vec[25], node_val_preload_vec[17]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+6][0]+os,merge_node_vec[merge_vec_idx[2]+6][0]+os,merge_node_vec[merge_vec_idx[2]+2][0]+os))
======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[2]+4][0], merge_node_vec[merge_vec_idx[2]+0][0]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+2][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[2]+6][0], merge_node_vec[merge_vec_idx[2]+2][0]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+2][0]+os,merge_node_vec[merge_vec_idx[2]+2][0]+os,merge_node_vec[merge_vec_idx[2]+0][0]+os))

=========================================================================
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+5][0],valMod2_vec_level[0][0],tmp7,node_val_preload_vec[20]))
======>>>>>
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 1][0], valMod2_vec_level[0][0], node_val_preload_vec[24], node_val_preload_vec[16]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+5][0]+os,merge_node_vec[merge_vec_idx[2]+5][0]+os,merge_node_vec[merge_vec_idx[2]+1][0]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+7][0],valMod2_vec_level[0][0],tmp9,node_val_preload_vec[22]))
======>>>>>
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 3][0], valMod2_vec_level[0][0], node_val_preload_vec[26], node_val_preload_vec[18]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+7][0]+os,merge_node_vec[merge_vec_idx[2]+7][0]+os,merge_node_vec[merge_vec_idx[2]+3][0]+os))
======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[2]+5][0], merge_node_vec[merge_vec_idx[2]+1][0]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+3][0], valMod2_vec_level[1][0], merge_node_vec[merge_vec_idx[2]+7][0], merge_node_vec[merge_vec_idx[2]+3][0]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+3][0]+os,merge_node_vec[merge_vec_idx[2]+3][0]+os,merge_node_vec[merge_vec_idx[2]+1][0]+os))
=========================================================================
# after valMod2_vec_level[2][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][0], valMod2_vec_level[2][0], merge_node_vec[merge_vec_idx[2]+2][0], merge_node_vec[merge_vec_idx[2]+0][0]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][0], valMod2_vec_level[2][0], merge_node_vec[merge_vec_idx[2]+3][0], merge_node_vec[merge_vec_idx[2]+1][0]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+1][0]+os,merge_node_vec[merge_vec_idx[2]+1][0]+os,merge_node_vec[merge_vec_idx[2]+0][0]+os))
# after valMod2_vec_level[3][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[0], valMod2_vec_level[3][0], merge_node_vec[merge_vec_idx[2]+1][0], merge_node_vec[merge_vec_idx[2]+0][0]))

==================================================================================================================================================================
# for 2
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+4][2],valMod2_vec_level[0][2],tmp6,node_val_preload_vec[19]))
======>>>>>
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 0][2], valMod2_vec_level[0][2], node_val_preload_vec[23], node_val_preload_vec[15]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+4][2]+os,merge_node_vec[merge_vec_idx[2]+4][2]+os,merge_node_vec[merge_vec_idx[2]+0][2]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+6][2],valMod2_vec_level[0][2],tmp8,node_val_preload_vec[21]))
======>>>>>
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 2][2], valMod2_vec_level[0][2], node_val_preload_vec[25], node_val_preload_vec[17]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+6][2]+os,merge_node_vec[merge_vec_idx[2]+6][2]+os,merge_node_vec[merge_vec_idx[2]+2][2]+os))
======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[2]+4][2], merge_node_vec[merge_vec_idx[2]+0][2]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+2][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[2]+6][2], merge_node_vec[merge_vec_idx[2]+2][2]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+2][2]+os,merge_node_vec[merge_vec_idx[2]+2][2]+os,merge_node_vec[merge_vec_idx[2]+0][2]+os))

=========================================================================
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+5][2],valMod2_vec_level[0][2],tmp7,node_val_preload_vec[20]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 1][2], valMod2_vec_level[0][2], node_val_preload_vec[24], node_val_preload_vec[16]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+5][2]+os,merge_node_vec[merge_vec_idx[2]+5][2]+os,merge_node_vec[merge_vec_idx[2]+1][2]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+7][2],valMod2_vec_level[0][2],tmp9,node_val_preload_vec[22]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 3][2], valMod2_vec_level[0][2], node_val_preload_vec[26], node_val_preload_vec[18]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+7][2]+os,merge_node_vec[merge_vec_idx[2]+7][2]+os,merge_node_vec[merge_vec_idx[2]+3][2]+os))
======================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[2]+5][2], merge_node_vec[merge_vec_idx[2]+1][2]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+3][2], valMod2_vec_level[1][2], merge_node_vec[merge_vec_idx[2]+7][2], merge_node_vec[merge_vec_idx[2]+3][2]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+3][2]+os,merge_node_vec[merge_vec_idx[2]+3][2]+os,merge_node_vec[merge_vec_idx[2]+1][2]+os))
=========================================================================
# after valMod2_vec_level[2][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][2], valMod2_vec_level[2][2], merge_node_vec[merge_vec_idx[2]+2][2], merge_node_vec[merge_vec_idx[2]+0][2]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][2], valMod2_vec_level[2][2], merge_node_vec[merge_vec_idx[2]+3][2], merge_node_vec[merge_vec_idx[2]+1][2]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+1][2]+os,merge_node_vec[merge_vec_idx[2]+1][2]+os,merge_node_vec[merge_vec_idx[2]+0][2]+os))

# after valMod2_vec_level[3][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[2], valMod2_vec_level[3][2], merge_node_vec[merge_vec_idx[2]+1][2], merge_node_vec[merge_vec_idx[2]+0][2]))

==================================================================================================================================================================
# for 1
======================================
# after valMod2_vec_level[0][0] available
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+4][1],valMod2_vec_level[0][1],tmp6,node_val_preload_vec[19]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 0][1], valMod2_vec_level[0][1], node_val_preload_vec[23], node_val_preload_vec[15]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+4][1]+os,merge_node_vec[merge_vec_idx[2]+4][1]+os,merge_node_vec[merge_vec_idx[2]+0][1]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+6][1],valMod2_vec_level[0][1],tmp8,node_val_preload_vec[21]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 2][1], valMod2_vec_level[0][1], node_val_preload_vec[25], node_val_preload_vec[17]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+6][1]+os,merge_node_vec[merge_vec_idx[2]+6][1]+os,merge_node_vec[merge_vec_idx[2]+2][1]+os))
=========================================================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[2]+4][1], merge_node_vec[merge_vec_idx[2]+0][1]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+2][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[2]+6][1], merge_node_vec[merge_vec_idx[2]+2][1]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+2][1]+os,merge_node_vec[merge_vec_idx[2]+2][1]+os,merge_node_vec[merge_vec_idx[2]+0][1]+os))
====================================================================================================
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+5][1],valMod2_vec_level[0][1],tmp7,node_val_preload_vec[20]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 1][1], valMod2_vec_level[0][1], node_val_preload_vec[24], node_val_preload_vec[16]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+5][1]+os,merge_node_vec[merge_vec_idx[2]+5][1]+os,merge_node_vec[merge_vec_idx[2]+1][1]+os))
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+7][1],valMod2_vec_level[0][1],tmp9,node_val_preload_vec[22]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 3][1], valMod2_vec_level[0][1], node_val_preload_vec[26], node_val_preload_vec[18]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+7][1]+os,merge_node_vec[merge_vec_idx[2]+7][1]+os,merge_node_vec[merge_vec_idx[2]+3][1]+os))
=========================================================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[2]+5][1], merge_node_vec[merge_vec_idx[2]+1][1]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+3][1], valMod2_vec_level[1][1], merge_node_vec[merge_vec_idx[2]+7][1], merge_node_vec[merge_vec_idx[2]+3][1]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+3][1]+os,merge_node_vec[merge_vec_idx[2]+3][1]+os,merge_node_vec[merge_vec_idx[2]+1][1]+os))

====================================================================================================
# after valMod2_vec_level[2][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][1], valMod2_vec_level[2][1], merge_node_vec[merge_vec_idx[2]+2][1], merge_node_vec[merge_vec_idx[2]+0][1]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][1], valMod2_vec_level[2][1], merge_node_vec[merge_vec_idx[2]+3][1], merge_node_vec[merge_vec_idx[2]+1][1]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+1][1]+os,merge_node_vec[merge_vec_idx[2]+1][1]+os,merge_node_vec[merge_vec_idx[2]+0][1]+os))
# after valMod2_vec_level[3][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[1], valMod2_vec_level[3][1], merge_node_vec[merge_vec_idx[2]+1][1], merge_node_vec[merge_vec_idx[2]+0][1]))
==================================================================================================================================================================
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+4][3],valMod2_vec_level[0][3],tmp6,node_val_preload_vec[19]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 0][3], valMod2_vec_level[0][3], node_val_preload_vec[23], node_val_preload_vec[15]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+4][3]+os,merge_node_vec[merge_vec_idx[2]+4][3]+os,merge_node_vec[merge_vec_idx[2]+0][3]+os))

======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+6][3],valMod2_vec_level[0][3],tmp8,node_val_preload_vec[21]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 2][3], valMod2_vec_level[0][3], node_val_preload_vec[25], node_val_preload_vec[17]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+6][3]+os,merge_node_vec[merge_vec_idx[2]+6][3]+os,merge_node_vec[merge_vec_idx[2]+2][3]+os))

=========================================================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[2]+4][3], merge_node_vec[merge_vec_idx[2]+0][3]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+2][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[2]+6][3], merge_node_vec[merge_vec_idx[2]+2][3]))

                    for os in range(0,8):

                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+2][3]+os,merge_node_vec[merge_vec_idx[2]+2][3]+os,merge_node_vec[merge_vec_idx[2]+0][3]+os))
====================================================================================================
======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+5][3],valMod2_vec_level[0][3],tmp7,node_val_preload_vec[20]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 1][3], valMod2_vec_level[0][3], node_val_preload_vec[24], node_val_preload_vec[16]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+5][3]+os,merge_node_vec[merge_vec_idx[2]+5][3]+os,merge_node_vec[merge_vec_idx[2]+1][3]+os))

======================================
                    instr["valu"].append(("multiply_add",merge_node_vec[merge_vec_idx[2]+7][3],valMod2_vec_level[0][3],tmp9,node_val_preload_vec[22]))
                    instr["flow"].append(("vselect", merge_node_vec[merge_vec_idx[2]+ 3][3], valMod2_vec_level[0][3], node_val_preload_vec[26], node_val_preload_vec[18]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+7][3]+os,merge_node_vec[merge_vec_idx[2]+7][3]+os,merge_node_vec[merge_vec_idx[2]+3][3]+os))

=========================================================================
# after valMod2_vec_level[1][0] available
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[2]+5][3], merge_node_vec[merge_vec_idx[2]+1][3]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+3][3], valMod2_vec_level[1][3], merge_node_vec[merge_vec_idx[2]+7][3], merge_node_vec[merge_vec_idx[2]+3][3]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+3][3]+os,merge_node_vec[merge_vec_idx[2]+3][3]+os,merge_node_vec[merge_vec_idx[2]+1][3]+os))
====================================================================================================
# after valMod2_vec_level[2][0] available

                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+0][3], valMod2_vec_level[2][3], merge_node_vec[merge_vec_idx[2]+2][3], merge_node_vec[merge_vec_idx[2]+0][3]))
                    instr["valu"].append(("multiply_add", merge_node_vec[merge_vec_idx[2]+1][3], valMod2_vec_level[2][3], merge_node_vec[merge_vec_idx[2]+3][3], merge_node_vec[merge_vec_idx[2]+1][3]))

                    for os in range(0,8):
                        instr["alu"].append(("-",merge_node_vec[merge_vec_idx[2]+1][3]+os,merge_node_vec[merge_vec_idx[2]+1][3]+os,merge_node_vec[merge_vec_idx[2]+0][3]+os))
# after valMod2_vec_level[3][0] available
                    instr["valu"].append(("multiply_add", node_val_vec[3], valMod2_vec_level[3][3], merge_node_vec[merge_vec_idx[2]+1][3], merge_node_vec[merge_vec_idx[2]+0][3]))
==================================================================================================================================================================