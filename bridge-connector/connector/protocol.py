from typing import Dict, List


calls_subscription = {
    "index": 1,
    "type": "calls",
    "elements": [
        "name",
        # note: these are handled by call_info_subscription below
        # "participants", "distributedInstances", "recording", "endpointRecording", "streaming", "lockState",
        # "callType", "callCorrelator"
    ]
}


def call_info_subscription(call_id: str, ind: int):
    return {"index": ind,
            "type": "callInfo",
            "call": call_id,
            "elements": ["name", "participants", "distributedInstances", "recording",
                         "endpointRecording", "streaming", "lockState", "callType",
                         "callCorrelator", "joinAudioMuteOverride"]
            }


def call_roster_subscription(call_id: str, ind: int):
    return {"index": ind,
            "type": "callRoster",
            "call": call_id,
            "elements": ["name", "uri", "state", "direction", "audioMuted", "videoMuted",
                         "importance", "layout", "activeSpeaker", "presenter",
                         "endpointRecording", "canMove", "movedParticipant",
                         "movedParticipantCallBridge"]}


def subscription_request(subscriptions: List[Dict], message_id: int):
    return {"type": "message",
            "message":
                {"messageId": message_id,
                 "type": "subscribeRequest",
                 "subscriptions": subscriptions
                 }}


def ack(message_id: int):
    return {"type": "messageAck",
            "messageAck":
                {"messageId": message_id,
                 "status": "success"}}
