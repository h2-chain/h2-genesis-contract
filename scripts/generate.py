import fileinput
import os
import re
import shutil
import subprocess

import jinja2
import typer
from typing_extensions import Annotated
from web3 import Web3

work_dir = os.getcwd()
if work_dir.endswith("scripts"):
    work_dir = work_dir[:-8]

network: str
chain_id: int
hex_chain_id: str

main = typer.Typer()


def backup_file(source, destination):
    try:
        shutil.copyfile(source, destination)
    except FileNotFoundError:
        print(f"Source file '{source}' not found.")
    except PermissionError:
        print(f"Permission error: Unable to copy file '{source}' to '{destination}'.")
    except Exception as e:
        print(f"An error occurred: {e}")


def insert(contract, pattern, ins):
    pattern = re.compile(pattern)
    filepath = os.path.join(work_dir, "contracts", contract)

    found = False
    with fileinput.FileInput(filepath, inplace=True) as file:
        for line in file:
            if not found and pattern.search(line):
                print(ins)
                found = True
            print(line, end="")

    if not found:
        raise Exception(f"{pattern} not found")


def replace(contract, pattern, repl, count=1):
    pattern = re.compile(pattern)
    filepath = os.path.join(work_dir, "contracts", contract)

    with open(filepath, "r") as f:
        content = f.read()

    if pattern.search(content):
        content = pattern.sub(repl, content, count=count)
    else:
        raise Exception(f"{pattern} not found")

    with open(filepath, "w") as f:
        f.write(content)


def replace_parameter(contract, parameter, value):
    pattern = f"{parameter} =[^;]*;"
    repl = f"{parameter} = {value};"

    replace(contract, pattern, repl)


def convert_chain_id(int_chain_id: int):
    try:
        hex_representation = hex(int_chain_id)[2:]
        padded_hex = hex_representation.zfill(4)
        return padded_hex
    except Exception as e:
        print(f"Error converting {int_chain_id} to hex: {e}")
        return None


def generate_from_template(data, template_file, output_file):
    template_loader = jinja2.FileSystemLoader(work_dir)
    template_env = jinja2.Environment(loader=template_loader, autoescape=True)

    template = template_env.get_template(template_file)
    result_string = template.render(data)

    output_path = os.path.join(work_dir, output_file)
    with open(output_path, "w") as output_file:
        output_file.write(result_string)


def generate_slash_indicator(misdemeanor_threshold, felony_threshold, init_felony_slash_scope):
    contract = "SlashIndicator.sol"
    backup_file(
        os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
    )

    replace_parameter(contract, "uint256 public constant MISDEMEANOR_THRESHOLD", f"{misdemeanor_threshold}")
    replace_parameter(contract, "uint256 public constant FELONY_THRESHOLD", f"{felony_threshold}")
    replace_parameter(contract, "uint256 public constant INIT_FELONY_SLASH_SCOPE", f"{init_felony_slash_scope}")

    if network == "dev":
        insert(contract, "alreadyInit = true;", "\t\tenableMaliciousVoteSlash = true;")


def generate_stake_hub(
    breathe_block_interval, max_elected_validators, unbond_period, downtime_jail_time, felony_jail_time,
    stake_hub_protector
):
    contract = "StakeHub.sol"
    backup_file(
        os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
    )

    replace_parameter(contract, "uint256 public constant BREATHE_BLOCK_INTERVAL", f"{breathe_block_interval}")

    replace(contract, r"maxElectedValidators = .*;", f"maxElectedValidators = {max_elected_validators};")
    replace(contract, r"unbondPeriod = .*;", f"unbondPeriod = {unbond_period};")
    replace(contract, r"downtimeJailTime = .*;", f"downtimeJailTime = {downtime_jail_time};")
    replace(contract, r"felonyJailTime = .*;", f"felonyJailTime = {felony_jail_time};")
    replace(contract, r"__Protectable_init_unchained\(.*\);", f"__Protectable_init_unchained({stake_hub_protector});")


def generate_governor(
    block_interval, init_voting_delay, init_voting_period, init_proposal_threshold, init_quorum_numerator,
    propose_start_threshold, init_min_period_after_quorum, governor_protector
):
    contract = "Governor.sol"
    backup_file(
        os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
    )

    replace_parameter(contract, "uint256 private constant BLOCK_INTERVAL", f"{block_interval}")
    replace_parameter(contract, "uint256 private constant INIT_VOTING_DELAY", f"{init_voting_delay}")
    replace_parameter(contract, "uint256 private constant INIT_VOTING_PERIOD", f"{init_voting_period}")
    replace_parameter(contract, "uint256 private constant INIT_PROPOSAL_THRESHOLD", f"{init_proposal_threshold}")
    replace_parameter(contract, "uint256 private constant INIT_QUORUM_NUMERATOR", f"{init_quorum_numerator}")
    replace_parameter(
        contract, "uint256 private constant PROPOSE_START_GOV_SUPPLY_THRESHOLD", f"{propose_start_threshold}"
    )
    replace_parameter(
        contract, "uint64 private constant INIT_MIN_PERIOD_AFTER_QUORUM", f"{init_min_period_after_quorum}"
    )
    replace(contract, r"__Protectable_init_unchained\(.*\);", f"__Protectable_init_unchained({governor_protector});")


def generate_timelock(init_minimal_delay):
    contract = "Timelock.sol"
    backup_file(
        os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
    )

    replace_parameter(contract, "uint256 private constant INIT_MINIMAL_DELAY", f"{init_minimal_delay}")


def generate_system():
    contract = "System.sol"
    backup_file(
        os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
    )

    replace_parameter(contract, "uint16 public constant chainID", f"0x{hex_chain_id}")


def generate_system_reward():
    if network == "dev":
        contract = "SystemReward.sol"
        backup_file(
            os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
        )

        insert(contract, "numOperator = 2;", "\t\toperators[VALIDATOR_CONTRACT_ADDR] = true;")
        insert(contract, "numOperator = 2;", "\t\toperators[SLASH_CONTRACT_ADDR] = true;")
        replace(contract, "numOperator = 2;", "numOperator = 4;")

def generate_validator_set(init_validator_set_bytes, init_burn_ratio):
    contract = "ValidatorSet.sol"
    backup_file(
        os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
    )

    replace_parameter(contract, "uint256 public constant INIT_BURN_RATIO", f"{init_burn_ratio}")
    replace_parameter(contract, "bytes public constant INIT_VALIDATORSET_BYTES", f"hex\"{init_validator_set_bytes}\"")


def generate_gov_hub():
    contract = "GovHub.sol"
    backup_file(
        os.path.join(work_dir, "contracts", contract), os.path.join(work_dir, "contracts", contract[:-4] + ".bak")
    )



def generate_genesis(output="./genesis.json"):
    subprocess.run(["forge", "build"], cwd=work_dir, check=True)
    subprocess.run(["node", "scripts/generate-genesis.js", "--chainId", f"{chain_id}", "--output", f"{output}"], cwd=work_dir, check=True)


@main.command(help="Generate contracts for H2 mainnet")
def mainnet():
    global network, chain_id, hex_chain_id
    network = "mainnet"
    chain_id = 2582
    hex_chain_id = convert_chain_id(chain_id)

    # mainnet init data
    init_burn_ratio = "1000"
    init_validator_set_bytes = "f9040f80f9040bf87194563322cc646b29348998b48f0a781a72de0e885b94563322cc646b29348998b48f0a781a72de0e885b94563322cc646b29348998b48f0a781a72de0e885b64b093c6fb41d8897eb68ad25e966de3cb309cbf1807da6e3032a88707fb80c9e4a98f110f72f6b7bba588c2c38017d8eab7f871944ddf403fab2c9953e87b713af8650b47a506e4e3944ddf403fab2c9953e87b713af8650b47a506e4e3944ddf403fab2c9953e87b713af8650b47a506e4e364b0a6450af15c45c559954660cf3d01d8cf6ed93c8f4a2ae147363274ceb21252bfc3544841ac5e63fd62508e544e3bd63af87194e1094a64b9e6a35cf504d97782084dd0208e49a894e1094a64b9e6a35cf504d97782084dd0208e49a894e1094a64b9e6a35cf504d97782084dd0208e49a864b090dc7f1c9792e2d2ab1461ee15c612d70b79819c24b3eaf74bee343e61766e02bfc912257e593955651d35ec14de3612f87194ef5e9de1e55cce5c86a19d71a9eebec286394b3394ef5e9de1e55cce5c86a19d71a9eebec286394b3394ef5e9de1e55cce5c86a19d71a9eebec286394b3364b09722fc855ae18ea61969c26f0fccd93296cc47d07e7e9d0ce445c6ee6a1d14eb2e7fef75dcd41bf4b0bca8ac95738adaf87194e11fe867fff43d89465b8d2e0db05dee5504d7ce94e11fe867fff43d89465b8d2e0db05dee5504d7ce94e11fe867fff43d89465b8d2e0db05dee5504d7ce64b093bc9190bf418f4f20db8c31f3111010138fcbdd6e3e98d5e360e4237d3eca4fef1aa39552557d8e812c86e6c4979933f871944ed4c4aa45a69c5be22c2ca646db0887b266b862944ed4c4aa45a69c5be22c2ca646db0887b266b862944ed4c4aa45a69c5be22c2ca646db0887b266b86264b0937bb0f0b8f504c3397b774f9d5e7127f4b9c15fda859410e873d55c4bdbd014566e082d9a1c8a1c38f36a634fbdd25bf871944615415aac8609577c4a2add55af25fecf5f862f944615415aac8609577c4a2add55af25fecf5f862f944615415aac8609577c4a2add55af25fecf5f862f64b081fbeb9dbca53bdc16da942059eb5327aac6c2929ae3b0348d5c55b786e2e44d32bc68483ddc3a4bb8dc598c41bdc396f871942e7ac7fb5c3ccb279b5c1168a117b4d0f3fb2cd2942e7ac7fb5c3ccb279b5c1168a117b4d0f3fb2cd2942e7ac7fb5c3ccb279b5c1168a117b4d0f3fb2cd264b090fbc2dc507a55c5dec905aa093b22b2956eb12e8cd861b2150b1077822ff4b0892cd363c5e68994fc37eacba4106609f87194632aab1ed1054d2a43d4077662abee5557e4645794632aab1ed1054d2a43d4077662abee5557e4645794632aab1ed1054d2a43d4077662abee5557e4645764b0b892aff71e0f9537e70adb94a80876c4b7f4859bac606f76fff6f08f30f0363ee2bc3e4a65f9b993b27c655657f69f49"

    block_interval = "1 seconds"
    breathe_block_interval = "1 days"
    max_elected_validators = "25"
    unbond_period = "7 days"
    downtime_jail_time = "2 days"
    felony_jail_time = "30 days"
    init_felony_slash_scope = "115200"
    misdemeanor_threshold = "200"
    felony_threshold = "600"
    init_voting_delay = "0 hours * 100 / 75"
    init_voting_period = "7 days * 100 / 75"
    init_proposal_threshold = "200 ether"
    init_quorum_numerator = "10"
    propose_start_threshold = "10_000_000 ether"
    init_min_period_after_quorum = "uint64(1 days * 100 / 75)"
    init_minimal_delay = "24 hours"
    
    stake_hub_protector = "0x1e5afE0Fd369f92CA1b8039f773a2B64697Ca5E8"
    governor_protector = "0x1e5afE0Fd369f92CA1b8039f773a2B64697Ca5E8"



    generate_system()
    generate_system_reward()
    generate_gov_hub()
    generate_slash_indicator(misdemeanor_threshold, felony_threshold, init_felony_slash_scope)
    generate_validator_set(init_validator_set_bytes, init_burn_ratio)
    generate_stake_hub(
        breathe_block_interval, max_elected_validators, unbond_period, downtime_jail_time, felony_jail_time,
        stake_hub_protector
    )
    generate_governor(
        block_interval, init_voting_delay, init_voting_period, init_proposal_threshold, init_quorum_numerator,
        propose_start_threshold, init_min_period_after_quorum, governor_protector
    )
    generate_timelock(init_minimal_delay)

    generate_genesis()
    print("Generate genesis of mainnet successfully")


@main.command(help="Generate contracts for H2 testnet")
def testnet():
    global network, chain_id, hex_chain_id
    network = "testnet"
    chain_id = 25821
    hex_chain_id = convert_chain_id(chain_id)

    # testnet init data
    init_burn_ratio = "1000"
    init_validator_set_bytes = "f9015d80f90159f87194035ba39085b3a149b1b186252e639f2fdeb6aa8c94035ba39085b3a149b1b186252e639f2fdeb6aa8c94035ba39085b3a149b1b186252e639f2fdeb6aa8c64b08ec997c9c836f53a48c21c433c9ddfea2be2f6ea15a1d058b634d42341f54197a7489d939d635ae4234fdc0f1bd7cce5f87194a29c7351b54aae166e4f651ef22eff1b47d49a2d94a29c7351b54aae166e4f651ef22eff1b47d49a2d94a29c7351b54aae166e4f651ef22eff1b47d49a2d64b08483e5b831c8b6a0a14c4db8c9b1fd81b8f2c5f28c2d2e0b2647b2399032834bea67ed48c1efc3b7ce98e66458332bc2f871940931f2a9a600eb04d216f15da75ece6769717b89940931f2a9a600eb04d216f15da75ece6769717b89940931f2a9a600eb04d216f15da75ece6769717b8964b095a1471f5671cc92ed80f8246d056f1cb379b57fb7122e572715140ef15223c1a5db3a7822f12286fe0c4112592ae677"

    block_interval = "1 seconds"
    breathe_block_interval = "1 days"
    max_elected_validators = "25"
    unbond_period = "7 days"
    downtime_jail_time = "2 days"
    felony_jail_time = "30 days"
    init_felony_slash_scope = "115200"
    misdemeanor_threshold = "200"
    felony_threshold = "600"
    init_voting_delay = "0 hours * 100 / 75"
    init_voting_period = "1 hours * 100 / 75"
    init_proposal_threshold = "200 ether"
    init_quorum_numerator = "10"
    propose_start_threshold = "10_000_000 ether"
    init_min_period_after_quorum = "uint64(0)"
    init_minimal_delay = "0 hours"

    stake_hub_protector = "0x28e14eAc4e41E146ECA05A9679604A0fE6959A39"
    governor_protector = "0x28e14eAc4e41E146ECA05A9679604A0fE6959A39"

    generate_system()
    generate_system_reward()
    generate_gov_hub()
    generate_slash_indicator(misdemeanor_threshold, felony_threshold, init_felony_slash_scope)
    generate_validator_set(init_validator_set_bytes, init_burn_ratio)
    generate_stake_hub(
        breathe_block_interval, max_elected_validators, unbond_period, downtime_jail_time, felony_jail_time,
        stake_hub_protector
    )
    generate_governor(
        block_interval, init_voting_delay, init_voting_period, init_proposal_threshold, init_quorum_numerator,
        propose_start_threshold, init_min_period_after_quorum, governor_protector
    )
    generate_timelock(init_minimal_delay)

    generate_genesis()
    print("Generate genesis of testnet successfully")


@main.command(help="Generate contracts for dev environment")
def dev(
    dev_chain_id: int = 714,
    init_burn_ratio: Annotated[str, typer.Option(help="init burn ratio of validatorSet")] = "1000",
    source_chain_id: Annotated[
        str, typer.Option(help="source chain id of the token recover portal")] = "Binance-Chain-Ganges",
    stake_hub_protector: Annotated[str, typer.Option(help="assetProtector of StakeHub")] = "address(0xdEaD)",
    governor_protector: Annotated[str, typer.Option(help="governorProtector of Governor")] = "address(0xdEaD)",
    block_interval: Annotated[str, typer.Option(help="block interval of Parlia")] = "3 seconds",
    breathe_block_interval: Annotated[str, typer.Option(help="breath block interval of Parlia")] = "1 days",
    max_elected_validators: Annotated[str, typer.Option(help="maxElectedValidators of StakeHub")] = "45",
    unbond_period: Annotated[str, typer.Option(help="unbondPeriod of StakeHub")] = "7 days",
    downtime_jail_time: Annotated[str, typer.Option(help="downtimeJailTime of StakeHub")] = "2 days",
    felony_jail_time: Annotated[str, typer.Option(help="felonyJailTime of StakeHub")] = "30 days",
    init_felony_slash_scope: str = "28800",
    misdemeanor_threshold: str = "50",
    felony_threshold: str = "150",
    init_voting_delay: Annotated[str,
                                 typer.Option(help="INIT_VOTING_DELAY of Governor")] = "0 hours / BLOCK_INTERVAL",
    init_voting_period: Annotated[str,
                                  typer.Option(help="INIT_VOTING_PERIOD of Governor")] = "7 days / BLOCK_INTERVAL",
    init_proposal_threshold: Annotated[str, typer.Option(help="INIT_PROPOSAL_THRESHOLD of Governor")] = "200 ether",
    init_quorum_numerator: Annotated[str, typer.Option(help="INIT_QUORUM_NUMERATOR of Governor")] = "10",
    propose_start_threshold: Annotated[
        str, typer.Option(help="PROPOSE_START_GOV_SUPPLY_THRESHOLD of Governor")] = "10_000_000 ether",
    init_min_period_after_quorum: Annotated[
        str, typer.Option(help="INIT_MIN_PERIOD_AFTER_QUORUM of Governor")] = "uint64(1 days / BLOCK_INTERVAL)",
    init_minimal_delay: Annotated[str, typer.Option(help="INIT_MINIMAL_DELAY of Timelock")] = "24 hours",
):
    global network, chain_id, hex_chain_id
    network = "dev"
    chain_id = dev_chain_id
    hex_chain_id = convert_chain_id(chain_id)

    try:
        result = subprocess.run(
            [
                "node", "-e",
                "const exportsObj = require(\'./scripts/validators.js\'); console.log(exportsObj.validatorSetBytes.toString(\'hex\'));"
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=work_dir
        )
        init_validator_set_bytes = result.stdout.strip()[2:]
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error getting init_validatorset_bytes: {e}")

    generate_system()
    generate_system_reward()
    generate_gov_hub()
    generate_slash_indicator(misdemeanor_threshold, felony_threshold, init_felony_slash_scope)
    generate_validator_set(init_validator_set_bytes, init_burn_ratio)
    generate_stake_hub(
        breathe_block_interval, max_elected_validators, unbond_period, downtime_jail_time, felony_jail_time,
        stake_hub_protector
    )
    generate_governor(
        block_interval, init_voting_delay, init_voting_period, init_proposal_threshold, init_quorum_numerator,
        propose_start_threshold, init_min_period_after_quorum, governor_protector
    )
    generate_timelock(init_minimal_delay)

    generate_genesis("./genesis-dev.json")
    print("Generate genesis of dev environment successfully")


@main.command(help="Recover from the backup")
def recover():
    contracts_dir = os.path.join(work_dir, "contracts")
    for file in os.listdir(contracts_dir):
        if file.endswith(".bak"):
            c_file = file[:-4] + ".sol"
            shutil.copyfile(os.path.join(contracts_dir, file), os.path.join(contracts_dir, c_file))
            os.remove(os.path.join(contracts_dir, file))

    print("Recover from the backup successfully")


@main.command(help="Generate init holders")
def generate_init_holders(
    init_holders: Annotated[str, typer.Argument(help="A list of addresses separated by comma")],
    template_file: str = "./scripts/init_holders.template",
    output_file: str = "./scripts/init_holders.js"
):
    init_holders = init_holders.split(",")
    data = {
        "initHolders": init_holders,
    }

    generate_from_template(data, template_file, output_file)
    print("Generate init holders successfully")


@main.command(help="Generate validators")
def generate_validators(
    file_path: str = "./validators.conf",
    template_file: str = "./scripts/validators.template",
    output_file: str = "./scripts/validators.js"
):
    file_path = os.path.join(work_dir, file_path)
    validators = []

    with open(file_path, "r") as file:
        for line in file:
            vs = line.strip().split(",")
            if len(vs) != 5:
                raise Exception(f"Invalid validator info: {line}")
            validators.append(
                {
                    "consensusAddr": vs[0],
                    "feeAddr": vs[1],
                    "bbcFeeAddr": vs[2],
                    "votingPower": vs[3],
                    "bLSPublicKey": vs[4],
                }
            )

    data = {
        "validators": validators,
    }

    generate_from_template(data, template_file, output_file)
    print("Generate validators successfully")


@main.command(help="Generate errors signature")
def generate_error_sig(dir_path: str = "./contracts"):
    dir_path = os.path.join(work_dir, dir_path)

    annotation_prefix = "    // @notice signature: "
    error_pattern = re.compile(r"^\s{4}(error)\s([a-zA-Z]*\(.*\));\s$")
    annotation_pattern = re.compile(r"^\s{4}(//\s@notice\ssignature:)\s.*\s$")
    for file in os.listdir(dir_path):
        if file.endswith(".sol"):
            file_path = os.path.join(dir_path, file)
            with open(file_path) as f:
                content = f.readlines()
            for i, line in enumerate(content):
                if error_pattern.match(line):
                    error_msg = line[10:-2]
                    # remove variable names
                    match = re.search(r"\((.*?)\)", error_msg)
                    if match and match.group(1) != "":
                        variables = [v.split()[0].strip() for v in match.group(1).split(",")]
                        error_msg = re.sub(r"\((.*?)\)", f"({','.join(variables)})", error_msg)
                    sig = Web3.keccak(text=error_msg)[:4].hex()
                    annotation = annotation_prefix + sig + "\n"
                    # update/insert annotation
                    if annotation_pattern.match(content[i - 1]):
                        content[i - 1] = annotation
                    else:
                        content.insert(i, annotation)
            with open(file_path, "w") as f:
                f.writelines(content)


if __name__ == "__main__":
    main()
