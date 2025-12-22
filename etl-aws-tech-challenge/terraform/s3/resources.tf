resource "aws_s3_bucket" "fiap_etl_tech_challenge_2_mathvivas" {
    bucket = "fiap_etl_tech_challenge_2_mathvivas"
}

resource "aws_s3_object" "raw_path" {
    bucket = aws_s3_bucket.fiap_etl_tech_challenge_2_mathvivas.bucket
    key = "raw/"
}

resource "aws_s3_object" "interim_path" {
    bucket = aws_s3_bucket.fiap_etl_tech_challenge_2_mathvivas.bucket
    key = "interim/"
}

resource "aws_s3_object" "final_path" {
    bucket = aws_s3_bucket.fiap_etl_tech_challenge_2_mathvivas.bucket
    key = "final/"
}

resource "aws_s3_object" "query_results_path" {
    bucket = aws_s3_bucket.fiap_etl_tech_challenge_2_mathvivas.bucket
    key = "query-results/"
}

resource "aws_s3_object" "scripts_path" {
    bucket = aws_s3_bucket.fiap_etl_tech_challenge_2_mathvivas.bucket
    key = "scripts/"
}