import {Construct} from "constructs";

import {RemovalPolicy, Stack, StackProps} from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";

export class BackupStack extends Stack {
    private readonly backupUser: iam.User;
    private readonly backupRole: iam.Role;
    private readonly backupBucket: s3.Bucket;

    constructor(scope: Construct, id: string, props?: StackProps) {
        super(scope, id, props);

        this.backupUser = this.createBackupUser();
        this.backupRole = this.createBackupRole();
        this.backupBucket = this.createBackupBucket();
    }

    private qualifyName(name: string) {
        return `${name}-${this.region}`;
    }

    private createBackupUser(): iam.User {
        return new iam.User(this, "ResticBackupUser", {});
    }

    private createBackupRole(): iam.Role {
        return new iam.Role(this, "BackupRole", {assumedBy: this.backupUser});
    }

    private createBackupBucket(): s3.Bucket {
        const bucket = new s3.Bucket(this, "BackupBucket", {
            bucketName: this.qualifyName("layertwo-dev-backup"),
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            encryption: s3.BucketEncryption.S3_MANAGED,
            enforceSSL: true,
            versioned: true, // TODO consider
            removalPolicy: RemovalPolicy.RETAIN,
            lifecycleRules: [],
        });
        bucket.grantReadWrite(this.backupRole);
        return bucket;
    }
}
