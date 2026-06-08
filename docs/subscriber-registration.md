# Subscriber Registration

Subscribers must be registered in the free5GC WebUI before UEs can attach. This is a one-time setup step that persists in MongoDB across restarts. Re-registration is only required if the database volume is wiped.

---

## Access the WebUI

Go to http://localhost:5000 and log in with `admin` / `free5gc`.

---

## Create Subscribers

Navigate to Subscribers and create five subscribers. Only SUPI, SST, SD, and Static IP change per subscriber. All other fields are identical across all five.

**Common fields for all subscribers:**

- Authentication Management Field (AMF): `8000`
- Authentication Method: `5G_AKA`
- Operator Code Type: `OPc`
- Operator Code Value: `8e27b6af0e692e750f32667a3b14605d`
- Permanent Authentication Key: `8baf473f2f8fd09487cccbd7097c6862`
- Subscribed UE AMBR Uplink: `1 Gbps`
- Subscribed UE AMBR Downlink: `2 Gbps`
- DNN: `internet`
- Default 5QI: `9`
- Delete all pre-filled Flow Rules
- Delete all pre-filled S-NSSAI entries, then add one new S-NSSAI per subscriber

**Per-subscriber values:**

| Subscriber | SUPI | SST | SD | Static IP |
|------------|------|-----|-----|-----------|
| UE1 (VLE) | imsi-208930000000001 | 1 | 000001 | 10.60.1.1 |
| UE2 (Portal) | imsi-208930000000002 | 1 | 000002 | 10.60.2.1 |
| UE3 (Admin) | imsi-208930000000003 | 1 | 000003 | 10.60.3.1 |
| UE4 (IoT) | imsi-208930000000004 | 2 | 000004 | 10.60.4.1 |
| UE5 (General) | imsi-208930000000005 | 1 | 000005 | 10.60.5.1 |

To set the static IP, toggle the IPv4 Address switch ON inside the DNN configuration section and enter the IP. Click VERIFY to confirm the IP is within the configured static pool. It will only verify correctly after the SST and SD fields are set for that slice.
