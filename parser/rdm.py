import json

import MySQLdb as msd
import requests
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY

from config import config


class RDMStatusCollector(object):
    def __init__(self, registry=REGISTRY):
        registry.register(self)

    def collect(self):
        rdm_uptime = GaugeMetricFamily("rdm_uptime", "RDM Uptime")
        rdm_timestamp = GaugeMetricFamily("rdm_timestamp", "RDM Timestamp")

        rdm_devices_status = GaugeMetricFamily(
            "rdm_devices_status",
            "RDM Devices Status",
            labels=["state"],
        )
        rdm_active_pokemon = GaugeMetricFamily(
            "rdm_pokemon",
            "RDM Active Pokemon",
            labels=["state"],
        )
        rdm_processing = GaugeMetricFamily(
            "rdm_processing",
            "RDM Processing",
            labels=["state"],
        )

        rdm_device = GaugeMetricFamily(
            "rdm_device",
            "RDM Device",
            labels=["device_name", "instance_name"],
        )
        rdm_instance = GaugeMetricFamily(
            "rdm_instance",
            "RDM Instance",
            labels=["instance_name", "instance_type"],
        )

        rdm_account = GaugeMetricFamily(
            "rdm_account",
            "RDM Account",
            labels=["group", "failed"],
        )
        rdm_raid = GaugeMetricFamily(
            "rdm_raid",
            "RDM Raid",
            labels=["level"],
        )

        families = [
            rdm_uptime,
            rdm_timestamp,
            rdm_devices_status,
            rdm_active_pokemon,
            rdm_processing,
            rdm_device,
            rdm_instance,
            rdm_account,
            rdm_raid,
        ]

        accounts = {}
        raids = {}

        try:
            req = requests.get(
                f"{config['rdm']['url']}/api/get_data",
                params={
                    "show_status": "true",
                    "show_devices": "true",
                    "show_instances": "true",
                },
                auth=(config["rdm"]["username"], config["rdm"]["password"]),
                timeout=5,
            )

            # RDM API is returning -inf in some cases...
            data = req.text.replace("-inf", "null")
            req = json.loads(data)

            con = msd.connect(
                host=config["db"]["hostname"],
                user=config["db"]["username"],
                passwd=config["db"]["password"],
                db=config["db"]["database"],
                connect_timeout=config["db"]["timeout"],
            )
            cur = con.cursor()

            cur.execute(
                "SELECT count(*), failed, `group` "
                "FROM `account` "
                "GROUP BY failed, `group`"
            )
            for row in cur.fetchall():
                counter, fail_reason, group_name = row
                counter = int(counter)
                group_name = group_name.replace("disabled_", "")
                keyname = f"{group_name}:-:{fail_reason}"
                if keyname not in accounts:
                    accounts[keyname] = counter
                else:
                    accounts[keyname] += counter

            cur.execute(
                "SELECT count(*), raid_level "
                "FROM `gym` "
                "WHERE raid_level > 0 AND raid_end_timestamp > UNIX_TIMESTAMP() "
                "GROUP BY raid_level"
            )
            for row in cur.fetchall():
                counter, raid_level = int(row[0]), str(row[1])
                raids[raid_level] = counter

            con.close()

        except Exception as e:
            return families

        rdm_uptime.add_metric(["timestamp"], req["data"]["status"]["uptime"]["date"])
        rdm_timestamp.add_metric(["timestamp"], req["data"]["timestamp"])

        for key, value in req["data"]["status"]["devices"].items():
            rdm_devices_status.add_metric([key], value=value or 0)

        for key, value in req["data"]["status"]["pokemon"].items():
            rdm_active_pokemon.add_metric([key], value=value or 0)

        for key, value in req["data"]["status"]["processing"].items():
            rdm_processing.add_metric([key], value=value or 0)

        for device in req["data"]["devices"]:
            if not device["instance"]:
                continue

            # shouldn't do that
            last_seen_seconds = req["data"]["timestamp"] - device["last_seen"]
            rdm_device.add_metric(
                [device["uuid"], device["instance"]], value=last_seen_seconds
            )

        for instance in req["data"]["instances"]:
            # skip instances without active instances
            if not instance["count"] or not instance.get("status"):
                continue

            if (
                instance["type"] in ("Circle Raid", "Circle Smart Raid")
                and instance["count"]
            ):
                status = instance["status"]["scans_per_h"]

            elif (
                instance["type"] in ("Circle Pokemon", "Circle Smart Pokemon")
                and instance["count"]
            ):
                status = instance["status"]["round_time"]

            elif instance["type"] == "Auto Quest":
                current_total = max(
                    [
                        instance["status"]["quests"]["current_count_db"],
                        instance["status"]["quests"]["current_count_internal"],
                    ]
                )
                status = (
                    current_total / instance["status"]["quests"]["total_count"] * 100
                )

            elif instance["type"] == "Leveling":
                continue

            else:
                status = 0

            rdm_instance.add_metric([instance["name"], instance["type"]], value=status)

        for keyname, counter in accounts.items():
            group_name, fail_reason = keyname.split(":-:")
            rdm_account.add_metric([group_name, fail_reason], value=counter)

        for raid_level, counter in raids.items():
            rdm_raid.add_metric([raid_level], value=counter)

        return families


RDM_STATUS_COLLECTOR = RDMStatusCollector()
