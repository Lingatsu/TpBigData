from pyspark import SparkConf, SparkContext
from pyspark.sql import SQLContext
from prettytable import PrettyTable

conf = SparkConf().setAppName("MovieLensAnalysis").set("spark.local.dir", "/root/spark-temp")
sc = SparkContext(conf=conf)

sqlContext = SQLContext(sc)

movies_path = "./input/ml-latest-small/movies.csv"
ratings_path = "./input/ml-latest-small/ratings.csv"
tags_path = "./input/ml-latest-small/tags.csv"

movies_rdd = sc.textFile(movies_path)
ratings_rdd = sc.textFile(ratings_path)
tags_rdd = sc.textFile(tags_path)

def parse_movies(line):
    parts = line.split(',')
    if len(parts) < 3:
        return None
    return (int(parts[0].strip()), parts[1].strip().strip('"'), parts[2].strip())

def parse_ratings(line):
    parts = line.split(',')
    if len(parts) < 4:
        return None
    return (int(parts[1].strip()), float(parts[2].strip()))

def parse_tags(line):
    parts = line.split(',')
    if len(parts) < 3:
        return None
    return (int(parts[1].strip()), parts[2].strip())

header_movies = movies_rdd.first()
movies_rdd = movies_rdd.filter(lambda line: line != header_movies).map(parse_movies)

header_ratings = ratings_rdd.first()
ratings_rdd = ratings_rdd.filter(lambda line: line != header_ratings).map(parse_ratings)

header_tags = tags_rdd.first()
tags_rdd = tags_rdd.filter(lambda line: line != header_tags).map(parse_tags)

def explode_genres(movie):
    if movie is None:
        return []
    movieId, title, genres = movie
    genres_list = genres.split('|')
    return [(movieId, title, genre) for genre in genres_list]

movies_with_genres_rdd = movies_rdd.flatMap(explode_genres)

ratings_rdd = ratings_rdd.map(lambda x: (x[0], (x[1], 1))) \
                         .reduceByKey(lambda a, b: (a[0] + b[0], a[1] + b[1])) \
                         .mapValues(lambda x: x[0] / x[1])

movies_with_ratings = movies_with_genres_rdd.map(lambda x: (x[0], (x[1], x[2]))) \
                                            .join(ratings_rdd) \
                                            .map(lambda x: (x[1][0][1], x[1][0][0], x[1][1]))  

top_10_films_ratings = movies_with_ratings \
    .map(lambda x: (x[0], x[2])) \
    .distinct() \
    .sortBy(lambda x: -x[1]) \
    .take(10)

genre_counts = movies_with_genres_rdd \
    .map(lambda x: (x[2], 1)) \
    .reduceByKey(lambda a, b: a + b) \
    .sortBy(lambda x: -x[1])

def print_table(data, headers):
    table = PrettyTable()
    table.field_names = headers
    for row in data:
        table.add_row(row)
    print(table)

print("Top 10 films par note moyenne:")
print_table(top_10_films_ratings, ["Title", "Average Rating"])

print("\nNombre de films pour chaque genre:")
genre_counts_data = genre_counts.collect()
print_table(genre_counts_data, ["Genre", "Count"])

sc.stop()