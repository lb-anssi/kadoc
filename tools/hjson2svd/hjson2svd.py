#!/usr/bin/env python3
# Copyright (c) 2025 ANSSI
# SPDX-License-Identifier: Apache-2.0

"""
Script to convert hjson files to SVD files

Parameters:
    - in  : input folder containing all hjson files
    - top : name of top entity, corresponding file 'top.hjson'
    - out : name of output file

All parameters are mandatory 
"""

__author__ = "Luc Bonnafoux"
__copyright__ = "Copyright (c) 2025 ANSSI"
__license__ = "Apache-2.0"
__version__ = "0.1"

import sys
import os
import argparse
import hjson
from typing import IO, Any

"""
Device SVD template according to:
    https://arm-software.github.io/CMSIS_5/SVD/html/elem_device.html
"""
svd_body_tmp = """<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance"\
 xs:noNamespaceSchemaLocation="CMSIS-SVD.xsd">\
{dev_vendor}{dev_vendorID}
\t<name>{dev_name}</name>{dev_series}
\t<version>{dev_version}</version>
\t<description>{dev_desc}</description>\
{dev_license}{dev_cpu}{dev_headerSystemFilename}{dev_headerDefinitionPrefix}
\t<addressUnitBits>{dev_addressUnitBits}</addressUnitBits>
\t<width>{dev_width}</width>\
{dev_size}{dev_access}{dev_protection}{dev_resetValue}{dev_resetMask}
\t<peripherals>{dev_periph}
\t</peripherals>\
{dev_vendorExtensions}
</device>"""

"""
Peripheral template according to:
    https://arm-software.github.io/CMSIS_5/SVD/html/elem_peripherals.html#elem_peripheral
"""
svd_periph_tmp = """
\t\t<peripheral{per_derivedFrom}>
\t\t\t<name>{per_name}</name>\
{per_version}{per_desc}{per_alternate}{per_groupName}{per_prepend}{per_append}\
{per_headerStructName}{per_disableCond}
\t\t\t<baseAddress>{per_base}</baseAddress>\
{per_size}{per_access}{per_protection}{per_resetValue}{per_resetMask}\
{per_addressBlock}{per_interrupts}{per_regs}\
\t\t</peripheral>"""

"""
Register template according to:
    https://arm-software.github.io/CMSIS_5/SVD/html/elem_registers.html#elem_register
"""
svd_reg_tmp = """
\t\t\t\t<register{reg_derivedFrom}>
\t\t\t\t\t<name>{reg_name}</name>\
{reg_display}{reg_desc}{reg_alternateGroup}{reg_alternateReg}\
\t\t\t\t\t<addressOffset>{reg_off}</addressOffset>\
{reg_size}{reg_access}{reg_protection}{reg_resetValue}{reg_resetMask}\
{reg_dataType}{reg_modWriteVal}{reg_writeConstr}{reg_readAction}\
{reg_fields}
\t\t\t\t</register>"""

"""
Field template according to:
    https://arm-software.github.io/CMSIS_5/SVD/html/elem_registers.html#elem_field
"""
svd_field_tmp = """
\t\t\t\t\t\t<field{fld_derivedFrom}>
\t\t\t\t\t\t\t<name>{fld_name}</name>\
{fld_desc}{fld_range}{fld_access}{fld_modWriteVal}{fld_writeConstr}{fld_readAction}\
{fld_enum}
\t\t\t\t\t\t</field>"""

"""
EnumeratedValue template according to:
    https://arm-software.github.io/CMSIS_5/SVD/html/elem_registers.html#elem_enumeratedValue
"""
svd_enum_tmp = """
\t\t\t\t\t\t\t\t<enumeratedValue>\
{enm_name}{enm_desc}{enm_value}
\t\t\t\t\t\t\t\t</enumeratedValue>"""

"""
Interrupt template according to:
    https://arm-software.github.io/CMSIS_5/SVD/html/elem_peripherals.html#elem_interrupt
"""
svd_int_tmp = """
\t\t\t<interrupt>
\t\t\t\t<name>{int_name}</name>\
{int_desc}\
\t\t\t\t<value>{int_value}</value>
\t\t\t</interrupt>"""

"""
AddressBlock template according to:
    https://arm-software.github.io/CMSIS_5/SVD/html/elem_peripherals.html#elem_addressBlock
"""
svd_add_tmp = """
\t\t\t<addressBlock>
\t\t\t\t<offset>{add_off}</offset>
\t\t\t\t<size>{add_size}</size>
\t\t\t\t<usage>{add_usage}</usage>\
{add_protection}
\t\t\t</addressBlock>"""

def generate_fields(fields: dict[str, Any]) -> str:
    """Generate SVD for a fields block"""
    fields_str: str = "\n\t\t\t\t\t<fields>"

    for f in fields:
        derived_from: str = ""

        if 'name' in f:
            name: str = f['name']
        else:
            print("Invalid field with no name for: "+str(f))
            name: str = ""
        
        if 'desc' in f:
            desc_full: str = f['desc'].replace("\n", "").replace("<", "")
            desc: str = "\n\t\t\t\t\t\t\t<description>"+desc_full+"</description>"
        else:
            desc: str = ""

        if 'bits' in f:
            range: str = "\n\t\t\t\t\t\t\t<bitRange>["+f['bits']+"]</bitRange>"
        else:
            range: str = ""

        access: str = ""
        mod_write_val: str = ""
        write_constr: str = ""
        read_action: str = ""

        if 'enum' in f:
            enum: str = "\n\t\t\t\t\t\t\t<enumeratedValues>"

            for e in f['enum']:
                if 'name' in e:
                    enum_name: str = "\n\t\t\t\t\t\t\t\t\t<name>"+e['name']+"</name>"
                else:
                    enum_name: str = ""

                if 'value' in e:
                    enum_value: str = "\n\t\t\t\t\t\t\t\t\t<value>"+e['value']+"</value>"
                else:
                    enum_value: str = ""

                if 'desc' in e:
                    desc_full: str = e['desc'].replace("\n", "").replace("<", "")
                    enum_desc: str = "\n\t\t\t\t\t\t\t\t\t<description>"+desc_full+"</description>"
                else:
                    enum_desc: str = ""

                enum += svd_enum_tmp.format(
                    enm_name = enum_name,
                    enm_desc = enum_desc,
                    enm_value = enum_value
                )

            enum += "\n\t\t\t\t\t\t\t</enumeratedValues>"
        else:
            enum: str = ""

        fields_str += svd_field_tmp.format(
            fld_derivedFrom = derived_from,
            fld_name        = name,
            fld_desc        = desc,
            fld_range       = range,
            fld_access      = access,
            fld_modWriteVal = mod_write_val,
            fld_writeConstr = write_constr,
            fld_readAction  = read_action,
            fld_enum        = enum
        )

    fields_str += "\n\t\t\t\t\t</fields>"

    return fields_str

def generate_periph_regs(registers: dict[str, Any], reg_size: int) -> tuple[str, int]:
    """Generate SVD for a peripheral"""

    periph_regs = "\n\t\t\t<registers>"
    offset = 0

    for r in registers:
        derived_from: str = ""

        if 'name' in r:
            name: str = r['name']
        else:
            print('Register missing name for: '+str(r))
            return ("", 0)
        
        display: str = ""

        if 'desc' in r:
            desc_full: str = r['desc'].replace("\n", "").replace("<", "")
            desc: str = "\n\t\t\t\t\t<description>"+desc_full+"</description>\n"
        else:
            desc: str = ""

        alternate_group: str = ""
        alternate_reg: str   = ""

        # Assume that all registers are packed
        reg_offset: str = str(hex(offset))

        offset += reg_size

        size: str = "\n\t\t\t\t\t<size>"+str(reg_size)+"</size>"

        if 'swaccess' in r:
            access: str = "\n\t\t\t\t\t<access>"+r['swaccess']+"</access>"
        else:
            access: str = ""

        protection: str = ""
        reset_value: str = ""
        reset_mask: str = ""
        data_type: str = ""
        mod_write_val: str = ""
        write_constr: str = ""
        read_action: str = ""

        if 'fields' in r:
            fields: str = generate_fields(r['fields'])
        else:
            fields: str = ""

        periph_regs += svd_reg_tmp.format(
            reg_derivedFrom  = derived_from,
            reg_name         = name,
            reg_display      = display,
            reg_desc         = desc,
            reg_alternateGroup = alternate_group,
            reg_alternateReg = alternate_reg,
            reg_off          = reg_offset,
            reg_size         = size,
            reg_access       = access,
            reg_protection   = protection,
            reg_resetValue   = reset_value,
            reg_resetMask    = reset_mask,
            reg_dataType     = data_type,
            reg_modWriteVal  = mod_write_val,
            reg_writeConstr  = write_constr,
            reg_readAction   = read_action,
            reg_fields       = fields
        )

    periph_regs += "\t\t\t</registers>"

    return (periph_regs, offset)

def generate_ints(interrupts: dict[str, Any]) -> str:
    """Generate SVD for interrupts block"""
    ints = ""

    for i in interrupts:
        if 'name' in i:
            name: str = i['name']
        else:
            print("Invalid interrupt for: "+str(i))
            return ""
        
        if 'desc' in i:
            desc_full: str = i['desc'].replace("\n", "").replace("<", "")
            desc: str = "\n\t\t\t\t<description>"+desc_full+"</description>\n"
        else:
            desc: str = ""
        
        # value is mandatory but missing from hjson
        value: str = "0"

        ints += svd_int_tmp.format(
            int_name  = name,
            int_desc  = desc,
            int_value = value
        )


    return ints


def generate_periph(periph_f: IO[str], reg_size: int, per_data: dict[str, Any]) -> str:
    """Generate SVD for one peripheral"""

    # TODO: for now do not use peripheral derivation
    derived: str = ""

    type_str: str = periph_f.read()
    type_data: dict[str, Any] = hjson.loads(type_str)

    # name is mandatory
    if 'name' in per_data:
        name: str = per_data['name']
    else:
        print("Missing peripheral name for: " + str(per_data))
        return ""
    
    version: str = ""
    
    if 'one_line_desc' in type_data:
        desc_full: str = type_data['one_line_desc'].replace("\n", "").replace("<", "")
        desc: str = "\n\t\t\t<description>"+desc_full+"</description>"
    else:
        desc: str = ""

    alternate: str = ""
    groupName: str = ""
    prepend: str   = ""
    append: str    = ""
    header: str    = ""
    disableCond: str = ""

    if 'base_addr' in per_data:
        base: str = per_data['base_addr']
    else:
        print("Missing base offset for: "+name)
        return ""
    
    size: str = "\n\t\t\t<size>"+str(reg_size)+"</size>"

    access: str = ""
    protection: str = ""
    reset_value: str = ""
    reset_mask: str = ""

    if 'interrupt_list' in type_data:
        interrupts: str = generate_ints(type_data['interrupt_list'])
    else:
        interrupts: str = ""

    if 'registers' in type_data:
        (registers, blk_size) = generate_periph_regs(type_data['registers'], reg_size)

        if blk_size == 0:
            print ("Invalid register block for: " + name)
            return ""
    else:
        registers: str = ""

    if 'regs' in per_data['base_addr']:
        offset: str = per_data['base_addr']['regs']
    else:
        offset: str = per_data['base_addr']

    address_block: str = svd_add_tmp.format(
        add_off   = offset,
        add_size  = str(blk_size),
        add_usage = "registers",
        add_protection = ""
    )

    return svd_periph_tmp.format(
        per_derivedFrom = derived,
        per_name        = name,
        per_version     = version,
        per_desc        = desc,
        per_alternate   = alternate,
        per_groupName   = groupName,
        per_prepend     = prepend,
        per_append      = append,
        per_headerStructName = header,
        per_disableCond = disableCond,
        per_base        = base,
        per_size        = size,
        per_access      = access,
        per_protection  = protection,
        per_resetValue  = reset_value,
        per_resetMask   = reset_mask,
        per_addressBlock = address_block,
        per_interrupts  = interrupts,
        per_regs        = registers
        )

def generate_peripherals(
        inputs: str, periph_list: dict[str, Any], reg_size: int) -> str:
    """Generate SVD for all peripherals within the list"""

    periph_svd = ""

    in_path = os.path.join(inputs, '')

    for p in periph_list:
        if 'type' in p:
            try:
                with open(in_path + p['type'] + '.hjson', 'r') as periph_f:
                    periph_svd += generate_periph(periph_f, reg_size, p)
            except OSError:
                print ("Missing periph file : " + p['type'])
        else:
            print ("Invalid periph, missing type")
            print (p)

    return periph_svd

def generate_device(input: str, dev_data: dict[str, Any]) -> str:
    """Generate SVD for a device"""
    dev_svd = ""

    # Gather data on the device

    # vendor and vendor_id not found in hjson
    vendor: str = ""
    vendor_id: str = ""

    # name mandatory
    if 'name' in dev_data:
        name: str = dev_data['name']
    else:
        print ("Device must have a name")
        return ""

    # series not found in hjson
    series: str = ""

    # version not found but mandatory, take arbitrary value
    version: str = "0.1"

    # description not found but mandatory, use name instead
    desc: str = dev_data['name']

    # license not found in hjson
    license: str = ""

    # cpu different name in top file, TODO
    core: str = ""

    # header not found in hjson
    header_system_filename: str = ""
    header_definition_prefix: str = ""

    # Set all size and width to hjson datawidth, it may not be true for all cores !
    if 'datawidth' in dev_data:
        address_unit_bits: str = dev_data['datawidth']
        width: str = dev_data['datawidth']
        try:
            size: int = int(dev_data['datawidth'])
        except ValueError:
            print ("Invalid register width")
            return ""
        size_str: str = "\n\t<size>"+str(size)+"</size>"
    else:
        print("Data width must be defined")
        return ""
    
    # access, protection, reset not found in hjson
    access: str = ""
    protection: str = ""
    reset_value: str = ""
    reset_mask: str = ""

    periph: str = generate_peripherals(input, dev_data['module'], size)

    # no vendor extensions
    vendor_ext: str = ""

    return svd_body_tmp.format(
        dev_vendor   = vendor,
        dev_vendorID = vendor_id,
        dev_name     = name,
        dev_series   = series,
        dev_version  = version,
        dev_desc     = desc,
        dev_license  = license,
        dev_cpu      = core,
        dev_headerSystemFilename   = header_system_filename,
        dev_headerDefinitionPrefix = header_definition_prefix,
        dev_addressUnitBits = address_unit_bits,
        dev_width    = width,
        dev_size     = size_str,
        dev_access   = access,
        dev_protection = protection,
        dev_resetValue = reset_value,
        dev_resetMask  = reset_mask,
        dev_periph     = periph,
        dev_vendorExtensions = vendor_ext
    )

def generate_svd(input: str, top: str, output: str):
    """Parse hjson and generate SVD"""
    print("Parse input file")

    with open(output, 'w') as out_f:
        in_path = os.path.join(input, '') # Add trailing slash if missing
        in_path = os.path.join(in_path, top)

        with open(in_path + '.hjson', 'r') as top_f:
            top_data = top_f.read()
            top_data = hjson.loads(top_data)

            out_f.write(generate_device(input, top_data))

def main(argv: list[str]):
    """Parse arguments and launch generation script"""

    parser = argparse.ArgumentParser(description="Generate SVD from hjson files")
    parser.add_argument("-i", "--input", required=True,
                        help="Path to input folder")
    parser.add_argument("-t", "--top", required=True,
                        help="Name of top module")
    parser.add_argument("-o", "--out", required=True,
                        help="Name of output file")    
    args = parser.parse_args(argv)

    # Generate SVD
    generate_svd(args.input, args.top, args.out)

if __name__ == "__main__":
    main(sys.argv[1:])

