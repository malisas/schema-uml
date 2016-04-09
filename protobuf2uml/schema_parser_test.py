#! /usr/bin/python
"""
Try obtaining field names from proto3 schema using the given python class

"""

#import simple_schema_pb2 as schema

from descriptor_pb2 import FileDescriptorSet #note: uses proto2!!
from google.protobuf import json_format


schema_in_message = FileDescriptorSet()
schema_in_message.MergeFromString(open('/home/malisa/Documents/OHSU_internship/bmeg/schema/v3/simple_schema.pb', "rb").read())

#print(json_format.MessageToJson(schema_in_message))

"""
list_fields = schema_in_message.ListFields()
for fielddescriptor, value in list_fields:
    print(fielddescriptor.name)
    print(value)
"""

"""
Basically I need to extract enums and messages

loop through schema_in_message.message_type (a repeated field?)

if schema_in_message has field enumType --> we know that schema_in_message.enumType is a repeated field...? 

"""
#at the highest level, i think i need to loop through all the files as well...
#print(schema_in_message.file.enumType)
#print(schema_in_message.ListFields())
#print(schema_in_message.file[0].ListFields())


#To get all enum_types:
#print(schema_in_message.file[0].enum_type)

#To get all message_types:
#print(schema_in_message.file[0].message_type)
#print(len(schema_in_message.file[0].message_type)) #6 messages in message_type


#print(schema_in_message.file[0].message_type[0])  #gives me back the Position object
#print(schema_in_message.file[0].message_type[0].name) #Position
#print(schema_in_message.file[0].message_type[0].field) #all the fields in Position
#print(schema_in_message.file[0].message_type[0].field[0]) #just the first field in Position, which is the reference_name
#print(schema_in_message.file[0].message_type[0].field[0].name)
#print(schema_in_message.file[0].message_type[0].field[0].type)

#checking the name tells me if there is an id reference. checking the type tells me if there is a containment (of message or enum). i.e. type is 11 or 14. then check type_name to get name of contained type.

