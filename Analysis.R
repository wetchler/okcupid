#------------------------------------------------------------------------------
#
# Analysis of OkCupid Profiles Data
# Albert Y. Kim (albert.kim@reed.edu) and Kristin Bott (bottk@reed.edu)
# Friday, January 24, 2014.
#
#------------------------------------------------------------------------------
# Import the CSV file containing the OKC data using the read.csv() function.
profiles <- read.csv(file="profiles.20120630.csv", header=TRUE)

# Delete essay responses to reduce data frame size
profiles <- profiles[, -which(substr(names(profiles), 1, 5) == "essay")]

dim(profiles)
names(profiles)
head(profiles)

#--------------------------------------------------------------------
# What are the genders and sexual orientations of the users? 
#--------------------------------------------------------------------
# Let's consider the sex of the users, which is a catergorial variable
profiles$sex

# This is overwhelming, let's count them
table(profiles$sex)

# To get proportions, we need a count of the number of users
n <- nrow(profiles)
table(profiles$sex) / n

# Generate a barplot to graph counts
barplot(table(profiles$sex), xlab="sex", ylab="count")

# Consider sexual orientation, another categorical variable
table(profiles$orientation)
table(profiles$orientation) / n
barplot(table(profiles$orientation), xlab="orientation", ylab="count")

# Now let's look at the crosstabs between the two variables via a "contingency"
# table
table(profiles$orientation, profiles$sex)
table(profiles$orientation, profiles$sex) / n

# One good way to visualize contigency tables is using a mosaicplot
pdf("gender_vs_orientation.pdf", height=6, width=6)
mosaicplot(table(profiles$sex, profiles$orientation), xlab="gender",
           ylab="orientation", main="Gender vs Orientation")
dev.off()


#--------------------------------------------------------------------
# How tall is everyone?
#--------------------------------------------------------------------
# Let's look at heights using a histogram
hist(profiles$height, xlab="Height (in inches)")

# Some people listed their heights as under 55 inches (4'7'') and over 80 inches
# (6'8'').  I'm suspicious of this.  Let's keep people who are 55 inches or more
# and 80 inches or less

# People greater than or equal to 55 inches
profiles$height >= 55
table(profiles$height >= 55)

# Less than or equal to 80 inches
table(profiles$height <= 80)

# Equal to 72 inches.  Note the double "==" operator
table(profiles$height == 72)

# Let's consider people who satisfy BOTH our desired conditions using the AND 
# operator "&"
profiles$height >= 55 & profiles$height <= 80
table(profiles$height >= 55 & profiles$height <= 80)

# Create subset of data consisting of only people with reasonable heights.
profiles.subset <- 
  subset(profiles, 
         profiles$height >= 55 & profiles$height <= 80)

# Let's compare the sizes of the original data frame and the new subsetted data
# frame
dim(profiles)
dim(profiles.subset)

# Let's generated a histogram to display the data.
hist(profiles.subset$height, xlab="Height (in inches)")

# Let's consider men and women's heights separately using the subset() command
# again.  i.e. take the subset of heights where sex is male.  Again, note the 
# double "=="
male.heights <- subset(profiles.subset$height, profiles.subset$sex=='m')
female.heights <- subset(profiles.subset$height, profiles.subset$sex=='f')

# par(mfrow=c(2,1)) allows us to show two plots at once
par(mfrow=c(2,1))
hist(female.heights)
hist(male.heights)

# Hard to compare.  Let's make the x-axis range and the number of 
# "buckets" in the histograms match
pdf("heights_split_by_gender.pdf", height=10, width=8)
par(mfrow=c(2,1))
hist(female.heights, xlim=c(55, 80), breaks=25, main="Female Heights",
     xlab="height in inches")
hist(male.heights, xlim=c(55, 80), breaks=25, main="Male Heights",
     xlab="height in inches")
dev.off()