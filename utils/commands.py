SW_COMMANDS = {
    
    #---START THE OVERALL PROCESS COMMAND---#
    1:{
        "cmd": "$START#",
        "ack": "START___START___",
        "is_ack": False,
        "sent_sts": False,
        "err_msg": "",
        "cmd_type": 0
    },

    #---STOP THE OVERALL PROCESS COMMAND---#
    2: {
        "cmd": "$STP#",
        "ack": "$ACK_STP#",
        "is_ack": False,
        "sent_sts": False,
        "err_msg": "",
        "cmd_type": 0
    }, 
    
}

CTRLR_COMMANDS = {
    
    #---START THE OVERALL PROCESS COMMAND---#
    "$STR#": {
        "ack": "$ACK_STR#",
        # "action": "start_process",
        # "args": True,
        "cmd_type": 0
    },

    #---STOP THE OVERALL PROCESS COMMAND---#
    "$STP#": {
        "ack": "$ACK_STP#",
        # "action": "stop_process",
        # "args": True,
        "cmd_type": 1
    },

}