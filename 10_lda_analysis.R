# Load libraries
library(tidyverse)
library(quanteda)
library(quanteda.textplots)
library(seededlda)

# Set working directory
setwd("C:/Users/Jain Farstrider/Desktop/dankuma")

# LDA analysis function
perform_lda_analysis <- function(data_file, output_prefix) {
  
  metadata <- read_csv(data_file, locale = locale(encoding = "UTF-8"))
  
  # Ensure unique document IDs
  metadata$unique_id <- paste0(output_prefix, "_", row.names(metadata))
  
  corpus_texts <- corpus(metadata, text_field = "text", docid_field = "unique_id")
  
  toks <- tokens(corpus_texts, remove_punct = FALSE, remove_numbers = FALSE)
  
  dfm <- dfm(toks)
  dfm_trimmed <- dfm_trim(dfm, min_docfreq = 0.01, docfreq_type = "prop")
  
  set.seed(42)
  lda <- textmodel_lda(dfm_trimmed, k = 10)
  
  lda.terms <- terms(lda, 20)
  
  write.csv(lda.terms, paste0("lda_analysis/", output_prefix, "_topics.csv"), 
            row.names = FALSE, fileEncoding = "UTF-8")
  
  mu <- lda$phi
  pi <- lda$theta
  
  metadata$dominant_topic <- apply(pi, 1, which.max)
  
  doc_topics <- as.data.frame(pi)
  colnames(doc_topics) <- paste0("topic_", 1:10)
  doc_topics$doc_id <- metadata$doc_id
  doc_topics$dominant_topic <- metadata$dominant_topic
  
  write.csv(doc_topics, paste0("lda_analysis/", output_prefix, "_doc_topics.csv"), 
            row.names = FALSE, fileEncoding = "UTF-8")
  
  png(paste0("lda_analysis/", output_prefix, "_topic_distribution.png"),
      width = 1000, height = 600)
  topic_counts <- table(metadata$dominant_topic)
  barplot(topic_counts, 
          main = paste(output_prefix, "Topic Distribution"),
          xlab = "Topic Number", 
          ylab = "Number of Documents",
          col = rainbow(10))
  dev.off()
  
  top_docs_list <- list()
  for (i in 1:10) {
    top_indices <- order(pi[, i], decreasing = TRUE)[1:min(10, nrow(metadata))]
    top_docs <- metadata[top_indices, c("doc_id", "bvid", "question_danmaku")]
    top_docs$topic_prob <- pi[top_indices, i]
    top_docs_list[[i]] <- top_docs
  }
  
  for (i in 1:10) {
    write.csv(top_docs_list[[i]], 
              paste0("lda_analysis/", output_prefix, "_topic", i, "_top_docs.csv"),
              row.names = FALSE, fileEncoding = "UTF-8")
  }
  
  return(list(lda = lda, dfm = dfm_trimmed, metadata = metadata, theta = pi, phi = mu))
}

# Run analysis
dir.create("lda_analysis", showWarnings = FALSE)

subtitle_result <- perform_lda_analysis("lda_analysis/subtitle_texts.csv", "subtitle")
danmaku_result <- perform_lda_analysis("lda_analysis/danmaku_texts.csv", "danmaku")
combined_result <- perform_lda_analysis("lda_analysis/combined_texts.csv", "combined")
