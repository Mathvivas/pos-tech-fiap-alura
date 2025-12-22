variable "role_name" {
    default = "fiap-etl-role"
}

variable "script_location" {
    default = "s3://fiap_etl_tech_challenge_2_mathvivas/scripts/"
}

variable "default_arguments" {
    type = map(string)
    default = {
        "--job-bookmark-option" = "job-bookmark-disable"
        "--enable-glue-datacatalog" = "true"
        "--additional-python-modules" = "ipeadatapy"
    }
}