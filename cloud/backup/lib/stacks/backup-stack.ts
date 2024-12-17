import {Construct} from "constructs";

import {Duration, RemovalPolicy, Stack, StackProps} from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";

export class BackupStack extends Stack {
    private readonly backupUser: iam.User;
    private readonly backupRole: iam.Role;
    private readonly backupBucket: s3.Bucket;

    constructor(scope: Construct, id: string, props?: StackProps) {
        super(scope, id, props);

        this.backupBucket = this.createBackupBucket();

        this.backupUser = this.createBackupUser();
        this.backupRole = this.createBackupRole();
    }

    private qualifyName(name: string) {
        return `${name}-${this.region}`;
    }

    private createBackupUser(): iam.User {
        const user = new iam.User(this, "VolSyncUser", {userName: "volsync-user"});
        new iam.AccessKey(user, "AccessKey", {user});
        return user;
    }

    private createBackupRole(): iam.Role {
        const role = new iam.Role(this, "BackupRole", {
            roleName: "layertwo-backup-role",
            assumedBy: this.backupUser,
        });
        this.backupBucket.grantReadWrite(role);
        return role;
    }

    private createBackupBucket(): s3.Bucket {
        return new s3.Bucket(this, "BackupBucket", {
            bucketName: this.qualifyName("layertwo-dev-backup"),
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            encryption: s3.BucketEncryption.S3_MANAGED,
            enforceSSL: true,
            versioned: true, // TODO consider
            removalPolicy: RemovalPolicy.RETAIN,
            lifecycleRules: [
                {
                    id: "GlacierTransition",
                    enabled: true,
                    transitions: [
                        {
                            storageClass: s3.StorageClass.DEEP_ARCHIVE,
                            transitionAfter: Duration.days(14),
                        },
                    ],
                },
                {
                    id: "Expiration",
                    enabled: true,
                    expiration: Duration.days(365),
                },
            ],
            autoDeleteObjects: false,
        });
    }
}
