
import math

import time

import exputil

from paper.satellite_networks_state.main_helper import MainHelper


BASE_NAME = f"kuiper_1156"
NICE_NAME = f"Kuiper-1156"

NUM_ORBS = 34
NUM_SATS_PER_ORB = 34
INCLINATION_DEGREE = 59.9
ALTITUDE_M = 1000*630
AOE = 35.0

######################################################################
# network dynamic state over time
######################################################################

EARTH_RADIUS = 6378135.0
G = 6.67408 * 10**(-11)
MASS = 5.9722*(10**24)
ECCENTRICITY = 0.0000001
ARG_OF_PERIGEE_DEGREE = 0.0
PHASE_DIFF = True

MEAN_MOTION_REV_PER_DAY = (
    24*60*60
)/(math.sqrt((4 * (math.pi**2) * (EARTH_RADIUS + ALTITUDE_M)**3)/(G * MASS)))
SATELLITE_CONE_RADIUS_M = ALTITUDE_M / math.tan(math.radians(AOE))

MAX_GSL_LENGTH_M = math.sqrt(
    math.pow(SATELLITE_CONE_RADIUS_M, 2) + math.pow(ALTITUDE_M, 2))

# ISLs are not allowed to dip below 80 km altitude in order to avoid weather conditions
MAX_ISL_LENGTH_M = 2 * \
    math.sqrt(math.pow(EARTH_RADIUS + ALTITUDE_M, 2) -
              math.pow(EARTH_RADIUS + 80000, 2))


main_helper = MainHelper(
    BASE_NAME,
    NICE_NAME,
    ECCENTRICITY,
    ARG_OF_PERIGEE_DEGREE,
    PHASE_DIFF,
    MEAN_MOTION_REV_PER_DAY,
    ALTITUDE_M,
    MAX_GSL_LENGTH_M,
    MAX_ISL_LENGTH_M,
    NUM_ORBS,
    NUM_SATS_PER_ORB,
    INCLINATION_DEGREE,
)

main_helper.calculate(
    "gen_data",
    200,  # duration_s
    1000,  # time_step_ms
    "isls_plus_grid",
    "ground_stations_top_100",
    "algorithm_free_one_only_over_isls",
    1,
)

######################################################################

# Core values
# 100 millisecond update interval
dynamic_state_update_interval_ms = 1000
simulation_end_time_s = 200                                     # 200 seconds
pingmesh_interval_ns = 1000 * 1000 * \
    1000                          # A ping every 1ms
# Enable utilization tracking
enable_isl_utilization_tracking = True
isl_utilization_tracking_interval_ns = 1 * 1000 * \
    1000 * 1000   # 1 second utilization intervals

# Derivatives
dynamic_state_update_interval_ns = dynamic_state_update_interval_ms * 1000 * 1000
simulation_end_time_ns = simulation_end_time_s * 1000 * 1000 * 1000

dynamic_state = "dynamic_state_" + \
    str(dynamic_state_update_interval_ms) + \
    "ms_for_" + str(simulation_end_time_s) + "s"

full_satellite_network_isls = f"{BASE_NAME}_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls"
chosen_pairs = [
    (f"{BASE_NAME}_isls", (NUM_ORBS*NUM_SATS_PER_ORB)+1, (NUM_ORBS *
     NUM_SATS_PER_ORB)+9, "TcpNewReno", full_satellite_network_isls),
    (f"{BASE_NAME}_isls", (NUM_ORBS*NUM_SATS_PER_ORB) +
     21, (NUM_ORBS*NUM_SATS_PER_ORB)+24, "TcpNewReno", full_satellite_network_isls),
    (f"{BASE_NAME}_isls", (NUM_ORBS*NUM_SATS_PER_ORB) +
     0, (NUM_ORBS*NUM_SATS_PER_ORB)+84, "TcpNewReno", full_satellite_network_isls),
]


def get_pings_run_list():

    # TCP transport protocol does not matter for the ping run
    reduced_chosen_pairs = []
    for p in chosen_pairs:
        if not (p[0], p[1], p[2], p[4]) in reduced_chosen_pairs:
            # Stripped out p[3] = transport protocol
            reduced_chosen_pairs.append((p[0], p[1], p[2], p[4]))

    run_list = []
    for p in reduced_chosen_pairs:
        run_list += [
            {
                "name": p[0] + "_" + str(p[1]) + "_to_" + str(p[2]) + "_pings",
                "satellite_network": p[3],
                "dynamic_state": dynamic_state,
                "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
                "simulation_end_time_ns": simulation_end_time_ns,
                "data_rate_megabit_per_s": 10000.0,
                "queue_size_pkt": 100000,
                "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
                "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
                "from_id": p[1],
                "to_id": p[2],
                "pingmesh_interval_ns": pingmesh_interval_ns,
            }
        ]

    return run_list


local_shell = exputil.LocalShell()

local_shell.remove_force_recursive("runs")
local_shell.remove_force_recursive("pdf")
local_shell.remove_force_recursive("data")

# Ping runs
for run in get_pings_run_list():

    # Prepare run directory
    run_dir = "runs/" + run["name"]
    local_shell.remove_force_recursive(run_dir)
    local_shell.make_full_dir(run_dir)

    # config_ns3.properties
    local_shell.copy_file(
        "paper/ns3_experiments/a_b/templates/template_pings_a_b_config_ns3.properties", run_dir + "/config_ns3.properties")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[SATELLITE-NETWORK]", str(run["satellite_network"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[DYNAMIC-STATE]", str(run["dynamic_state"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[DYNAMIC-STATE-UPDATE-INTERVAL-NS]", str(run["dynamic_state_update_interval_ns"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[SIMULATION-END-TIME-NS]", str(run["simulation_end_time_ns"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[ISL-DATA-RATE-MEGABIT-PER-S]", str(run["data_rate_megabit_per_s"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[GSL-DATA-RATE-MEGABIT-PER-S]", str(run["data_rate_megabit_per_s"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[ISL-MAX-QUEUE-SIZE-PKTS]", str(run["queue_size_pkt"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[GSL-MAX-QUEUE-SIZE-PKTS]", str(run["queue_size_pkt"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[ENABLE-ISL-UTILIZATION-TRACKING]", "true" if run["enable_isl_utilization_tracking"] else "false")
    if run["enable_isl_utilization_tracking"]:
        local_shell.sed_replace_in_file_plain(
            run_dir + "/config_ns3.properties",
            "[ISL-UTILIZATION-TRACKING-INTERVAL-NS-COMPLETE]",
            "isl_utilization_tracking_interval_ns=" +
            str(run["isl_utilization_tracking_interval_ns"])
        )
    else:
        local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                              "[ISL-UTILIZATION-TRACKING-INTERVAL-NS-COMPLETE]", "")
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[PINGMESH-INTERVAL-NS]", str(run["pingmesh_interval_ns"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[FROM]", str(run["from_id"]))
    local_shell.sed_replace_in_file_plain(run_dir + "/config_ns3.properties",
                                          "[TO]", str(run["to_id"]))

# Print finish
print("Success: generated runs")

local_shell = exputil.LocalShell()
max_num_processes = 1

# Check that no screen is running
if local_shell.count_screens() != 0:
    print("There is a screen already running. "
          "Please kill all screens before running this analysis script (killall screen).")
    exit(1)

commands_to_run = []
for run in get_pings_run_list():
    logs_ns3_dir = "runs/" + run["name"] + "/logs_ns3"
    local_shell.remove_force_recursive(logs_ns3_dir)
    local_shell.make_full_dir(logs_ns3_dir)
    # commands_to_run.append(
    #     "cd ../../../ns3-sat-sim/simulator; "
    #     "./waf --run=\"main_satnet --run_dir='../../paper/ns3_experiments/a_b/runs/" +
    #     run["name"] + "'\" "
    #     "2>&1 | tee '../../paper/ns3_experiments/a_b/" + logs_ns3_dir + "/console.txt'"
    # )
    commands_to_run.append(
        "cd ns3-sat-sim/simulator; "
        "./waf --run=\"main_satnet --run_dir='/mnt/Storage/Projects/hypatia/runs/" +
        run["name"] + "'\" "
        "2>&1 | tee '/mnt/Storage/Projects/hypatia/" + logs_ns3_dir + "/console.txt'"
    )

# Run the commands
print("Running commands (at most %d in parallel)..." % max_num_processes)
for i in range(len(commands_to_run)):
    print("Starting command %d out of %d: %s" %
          (i + 1, len(commands_to_run), commands_to_run[i]))
    local_shell.detached_exec(commands_to_run[i])
    while local_shell.count_screens() >= max_num_processes:
        time.sleep(2)

# Awaiting final completion before exiting
print("Waiting completion of the last %d..." % max_num_processes)
while local_shell.count_screens() > 0:
    time.sleep(2)
print("Finished.")

print(' > Plotting start')
# Ping runs
for run in get_pings_run_list():
    try:
        local_shell.make_full_dir("pdf/" + run["name"])
        local_shell.make_full_dir("data/" + run["name"])

        local_shell.perfect_exec(
            "cd ns3-sat-sim/simulator/contrib/basic-sim/tools/plotting/plot_ping; "
            "python plot_ping.py "
            "/mnt/Storage/Projects/hypatia/runs/" +
            run["name"] + "/logs_ns3 "
            "/mnt/Storage/Projects/hypatia/data/" +
            run["name"] + " "
            "/mnt/Storage/Projects/hypatia/pdf/" +
            run["name"] + " "
            "" + str(run["from_id"]) + " " + str(run["to_id"]) +
            " " + str(1 * 1000 * 1000 * 1000),  # from -> to
            # 1s interval
            output_redirect=exputil.OutputRedirect.CONSOLE
        )

    except Exception:
        print('--------------------------------------U')
        print(run)
        print('--------------------------------------D')

print(' > Complete.')
