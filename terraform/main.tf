# TEMPLATE ONLY - NOT plan/apply validated against a live tenancy.
# Built-in resource: OCI Compartment Quotas policy (oci_limits_quota).
# Field names per the oracle/oci provider docs. Conventions shown: the allowlist
# pattern - the broad 'zero' statement comes FIRST and the 'set' exception after,
# because within a policy a later statement supersedes an earlier one.

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0"
    }
  }
}

variable "tenancy_ocid" {
  type        = string
  description = "OCID of the tenancy (this example places the policy at the tenancy root)"
}

resource "oci_limits_quota" "govern_webshop" {
  compartment_id = var.tenancy_ocid
  name           = "govern-webshop-prod"
  description    = "Allowlist: only standard E4 cores in the webshop-prod compartment"

  statements = [
    # order matters: later statements supersede earlier ones for the same resource
    "zero compute-core quotas in compartment webshop-prod",
    "set compute-core quota standard-e4-core-count to 240 in compartment webshop-prod",
  ]
}
